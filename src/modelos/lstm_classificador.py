"""
Rede neural LSTM classificadora: lê a sequência das últimas 12 semanas.

Os outros modelos recebem variáveis prontas (variação dos casos em relação a 1-4 semanas
atrás, clima de S-1 a S-4). A LSTM recebe a série semana a semana e aprende sozinha quais
defasagens importam. Em cada uma das 12 semanas da janela (S-11 a S), a entrada é:
  - log dos casos daquela semana menos o log dos casos de S (escala relativa, como o alvo);
  - clima da semana anterior (temperatura média, chuva e umidade), padronizado com o treino.
Depois da sequência, a rede recebe o nível atual (log dos casos de S) e a semana do ano
(seno e cosseno), e devolve a probabilidade de cada tendência.

Uma única rede prevê os quatro horizontes ao mesmo tempo (uma saída por horizonte), o que
divide o custo de treino por quatro; experimento_classificadores.py usa
treinar_horizontes(). Para parar o treinamento, 15% dos municípios do treino ficam de
fora e servem de validação (early stopping): a rede para quando deixa de melhorar
nesses municípios, que é o mesmo tipo de generalização avaliado no projeto.

Requer as colunas de janela.adicionar_janela.
"""
import numpy as np
import pandas as pd
import torch
from torch import nn

from src.modelos.base import Classificador, tendencia_real
from src.modelos.janela import SEMANAS_JANELA
from src.modelos.lightgbm_classificador_clima import VARIAVEIS_CLIMA
from src.train import TENDENCIAS

FRACAO_PARADA = 0.15


class _Rede(nn.Module):
    def __init__(self, n_sequencia, n_estaticas, oculto, n_horizontes, dropout):
        super().__init__()
        self.n_horizontes = n_horizontes
        self.lstm = nn.LSTM(n_sequencia, oculto, batch_first=True)
        self.cabeca = nn.Sequential(nn.Linear(oculto + n_estaticas, oculto), nn.ReLU(), nn.Dropout(dropout),
                                    nn.Linear(oculto, n_horizontes * len(TENDENCIAS)))

    def forward(self, sequencia, estaticas):
        _, (oculto, _) = self.lstm(sequencia)
        return self.cabeca(torch.cat([oculto[-1], estaticas], dim=1)).view(-1, self.n_horizontes, len(TENDENCIAS))


class LSTMClassificador(Classificador):
    nome = 'lstm_classificador'
    descricao = 'Rede neural LSTM classificadora (sequência de 12 semanas de casos e clima)'
    multi_horizonte = True
    parametros = {'oculto': 32, 'dropout': 0.1, 'taxa': 1e-3, 'lote': 512, 'max_epocas': 40, 'paciencia': 5}

    # ------------------------------------------------------------ entradas
    def _entradas(self, df):
        semanas = SEMANAS_JANELA
        # Passo j da sequência = semana S-(semanas-1-j); var_log_k = log(S) - log(S-k)
        relativo = np.stack([-df[f'var_log_{semanas - 1 - j}'].to_numpy(float) if j < semanas - 1
                             else np.zeros(len(df)) for j in range(semanas)], axis=1)
        clima = np.stack([np.stack([df[f'{v}_s{semanas - j}'].to_numpy(float) for j in range(semanas)], axis=1)
                          for v in VARIAVEIS_CLIMA], axis=2)
        if not hasattr(self, 'media_clima'):
            self.media_clima = np.nanmean(clima, axis=(0, 1))
            self.desvio_clima = np.nanstd(clima, axis=(0, 1))
            self.media_nivel, self.desvio_nivel = df['log_casos'].mean(), df['log_casos'].std()
        clima = (clima - self.media_clima) / self.desvio_clima
        sequencia = np.concatenate([np.clip(relativo, -5, 5)[:, :, None], clima], axis=2)
        angulo = 2 * np.pi * df['semana_ano'].to_numpy(float) / 52.18
        estaticas = np.stack([(df['log_casos'].to_numpy(float) - self.media_nivel) / self.desvio_nivel,
                              np.sin(angulo), np.cos(angulo)], axis=1)
        return (torch.tensor(np.nan_to_num(sequencia), dtype=torch.float32),
                torch.tensor(np.nan_to_num(estaticas), dtype=torch.float32))

    # ------------------------------------------------------------ treino
    def treinar(self, df, horizonte):
        return self.treinar_horizontes({horizonte: df})

    def treinar_horizontes(self, dfs):
        """dfs: {horizonte: linhas de treino válidas para aquele horizonte}."""
        if self.threads > 0:
            torch.set_num_threads(self.threads)
        torch.manual_seed(self.semente)
        rng = np.random.default_rng(self.semente)
        self.horizontes = sorted(dfs)

        # Todas as linhas que têm alvo em pelo menos um horizonte; -1 onde não há alvo
        base = pd.concat(dfs.values())
        base = base[~base.index.duplicated()].sort_index()
        y = np.full((len(base), len(self.horizontes)), -1, dtype=np.int64)
        for i, h in enumerate(self.horizontes):
            pos = base.index.get_indexer(dfs[h].index)
            y[pos, i] = [TENDENCIAS.index(t) for t in tendencia_real(dfs[h], h)]

        cidades = base['cidade'].unique()
        parada = rng.choice(cidades, max(1, int(len(cidades) * FRACAO_PARADA)), replace=False)
        em_parada = base['cidade'].isin(parada).to_numpy()

        sequencia, estaticas = self._entradas(base[~em_parada])  # padronização com o treino
        seq_val, est_val = self._entradas(base[em_parada])
        y_tr, y_val = torch.tensor(y[~em_parada]), torch.tensor(y[em_parada])

        p = self.parametros
        self.rede = _Rede(sequencia.shape[2], estaticas.shape[1], p['oculto'], len(self.horizontes), p['dropout'])
        otimizador = torch.optim.Adam(self.rede.parameters(), lr=p['taxa'])
        perda = nn.CrossEntropyLoss(ignore_index=-1)
        melhor, melhor_estado, sem_melhora = np.inf, None, 0
        for _ in range(p['max_epocas']):
            self.rede.train()
            ordem = torch.randperm(len(y_tr))
            for ini in range(0, len(ordem), p['lote']):
                lote = ordem[ini:ini + p['lote']]
                otimizador.zero_grad()
                saida = self.rede(sequencia[lote], estaticas[lote])
                perda(saida.reshape(-1, len(TENDENCIAS)), y_tr[lote].reshape(-1)).backward()
                otimizador.step()
            self.rede.eval()
            with torch.no_grad():
                atual = perda(self.rede(seq_val, est_val).reshape(-1, len(TENDENCIAS)), y_val.reshape(-1)).item()
            if atual < melhor - 1e-4:
                melhor, sem_melhora = atual, 0
                melhor_estado = {k: v.clone() for k, v in self.rede.state_dict().items()}
            else:
                sem_melhora += 1
                if sem_melhora >= p['paciencia']:
                    break
        self.rede.load_state_dict(melhor_estado)
        self.rede.eval()
        return self

    # ------------------------------------------------------------ previsão
    def probabilidades(self, df, horizonte):
        if self.threads > 0:
            torch.set_num_threads(self.threads)
        sequencia, estaticas = self._entradas(df)
        with torch.no_grad():
            saida = self.rede(sequencia, estaticas)[:, self.horizontes.index(horizonte)]
            p = torch.softmax(saida, dim=1).numpy()
        return pd.DataFrame(p, columns=TENDENCIAS, index=df.index)
