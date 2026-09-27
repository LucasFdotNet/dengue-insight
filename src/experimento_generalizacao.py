"""
Experimento: generalização para municípios não vistos no treino.

Duas perguntas, respondidas só com os 100 municípios de treino (os 15 de validação
continuam intocados, como teste final):

1. Validação cruzada por município: qual configuração (sem clima ou com clima em
   diferentes janelas) prevê melhor municípios que o modelo nunca viu?
   Os 100 municípios são divididos em 5 grupos. Cada grupo é previsto por modelos
   treinados só com os outros 4, com a mesma validação walk-forward do train.py
   (retreino a cada 3 meses, para o experimento caber em tempo razoável). Assim, os
   100 municípios são avaliados "fora do treino", em vez de só os de validação.

2. Curva de aprendizado: quanto o erro cai com mais municípios no treino, e se ainda
   há ganho a esperar com mais municípios. Para cada grupo da validação cruzada,
   treina com n municípios sorteados entre os outros (n = 10, 20, 40, 60 e 80; 3
   sorteios por tamanho, retreino a cada 6 meses) e mede o erro no grupo separado.
   Ajusta a curva erro(n) = a + b * n^(-c): 'a' é o erro que se alcançaria com
   infinitos municípios.

Incerteza: intervalos de confiança de 95% por bootstrap sobre municípios (as semanas
de um mesmo município são muito correlacionadas; a unidade de amostragem é o
município). Nas comparações entre configurações, o bootstrap é pareado: os mesmos
municípios sorteados para as duas configurações.

Métrica principal: razão entre o erro absoluto médio do modelo e o do baseline de
persistência (abaixo de 1, o modelo é melhor), somando todas as semanas avaliadas.

Saídas:
  reports/generalizacao_configuracoes.csv   (validação cruzada por configuração)
  reports/generalizacao_curva.csv           (curva de aprendizado)
"""
import logging
import random

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from src.experimento_clima_semanal import adicionar_clima, configuracoes as configuracoes_clima
from src.train import FEATURES, HORIZONTES, avaliar_walk_forward, carregar, resumir_tendencia

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_CONFIG = 'reports/generalizacao_configuracoes.csv'
ARQUIVO_CURVA = 'reports/generalizacao_curva.csv'

N_GRUPOS = 5
SEMENTE = 42
MESES_RETREINO_CV = 3
MESES_RETREINO_CURVA = 6
TAMANHOS_CURVA = [10, 20, 40, 60, 80]
SORTEIOS_CURVA = 3
N_BOOTSTRAP = 2000
SEM_CLIMA = 'Sem clima'


def configuracoes():
    config = {SEM_CLIMA: FEATURES}
    for nome, features in configuracoes_clima().items():
        if features != FEATURES:
            config[nome] = features
    return config


def grupos_de_municipios(cidades):
    embaralhadas = sorted(cidades)
    random.Random(SEMENTE).shuffle(embaralhadas)
    return [embaralhadas[i::N_GRUPOS] for i in range(N_GRUPOS)]


def prever_fora_do_treino(dados, grupos, features, meses_por_retreino, horizontes=HORIZONTES, sorteio=None):
    """Previsões de cada grupo por modelos treinados sem ele (sorteio: n municípios de treino)."""
    partes = []
    for i, separado in enumerate(grupos):
        outros = [c for c in dados['cidade'].unique() if c not in separado]
        if sorteio is not None:
            outros = random.Random(SEMENTE + 1000 * sorteio[1] + i).sample(sorted(outros), sorteio[0])
        erros = avaliar_walk_forward(dados[dados['cidade'].isin(outros)], dados[dados['cidade'].isin(separado)],
                                     horizontes=horizontes, features=features,
                                     meses_por_retreino=meses_por_retreino)
        partes.append(erros[erros['Grupo'] == 'validacao'])
    return pd.concat(partes, ignore_index=True)


def erros_por_municipio(erros):
    """Soma dos erros absolutos do modelo e do baseline por município e horizonte."""
    return erros.assign(abs_m=erros['erro_lgbm'].abs(), abs_b=erros['erro_baseline'].abs()) \
        .groupby(['h', 'cidade'])[['abs_m', 'abs_b']].sum()


def bootstrap_razao(por_municipio, referencia=None):
    """Razão modelo/baseline (e diferença para a referência) com IC 95% por bootstrap de municípios."""
    rng = np.random.default_rng(SEMENTE)
    cidades = por_municipio.index.unique('cidade')
    linhas = []
    for h in HORIZONTES:
        pm = por_municipio.loc[h].reindex(cidades)
        ref = referencia.loc[h].reindex(cidades) if referencia is not None else None
        razao = pm['abs_m'].sum() / pm['abs_b'].sum()
        amostras, difs = [], []
        for _ in range(N_BOOTSTRAP):
            idx = rng.integers(0, len(cidades), len(cidades))
            s = pm.iloc[idx]
            r = s['abs_m'].sum() / s['abs_b'].sum()
            amostras.append(r)
            if ref is not None:
                sr = ref.iloc[idx]
                difs.append(r - sr['abs_m'].sum() / sr['abs_b'].sum())
        linha = {'h': h, 'Razao_MAE': razao,
                 'IC95_inf': np.percentile(amostras, 2.5), 'IC95_sup': np.percentile(amostras, 97.5)}
        if ref is not None:
            linha.update({'Dif_vs_sem_clima': razao - ref['abs_m'].sum() / ref['abs_b'].sum(),
                          'Dif_IC95_inf': np.percentile(difs, 2.5), 'Dif_IC95_sup': np.percentile(difs, 97.5)})
        linhas.append(linha)
    return pd.DataFrame(linhas)


def validacao_cruzada(dados, grupos):
    resultados, referencia = [], None
    for nome, features in configuracoes().items():
        logging.info(f"Validação cruzada: {nome} ({len(features)} variáveis)...")
        erros = prever_fora_do_treino(dados, grupos, features, MESES_RETREINO_CV)
        por_municipio = erros_por_municipio(erros)
        if nome == SEM_CLIMA:
            referencia = por_municipio
        tabela = bootstrap_razao(por_municipio, None if nome == SEM_CLIMA else referencia)
        tend = resumir_tendencia(erros).assign(h=lambda d: d['Horizonte'].str[-1].astype(int))
        tabela = tabela.merge(tend[['h', 'Acerto_modelo', 'Acerto_sempre_estavel', 'Subidas_detectadas',
                                    'Alarmes_subida_corretos', 'Sentido_oposto']], on='h')
        resultados.append(tabela.assign(Configuracao=nome, Municipios=por_municipio.index.unique('cidade').size))
    return pd.concat(resultados, ignore_index=True)


def curva_de_aprendizado(dados, grupos):
    linhas = []
    for n in TAMANHOS_CURVA:
        sorteios = 1 if n >= len(dados['cidade'].unique()) - max(len(g) for g in grupos) else SORTEIOS_CURVA
        for s in range(sorteios):
            logging.info(f"Curva de aprendizado: {n} municípios, sorteio {s + 1}/{sorteios}...")
            erros = prever_fora_do_treino(dados, grupos, FEATURES, MESES_RETREINO_CURVA, sorteio=(n, s))
            por_municipio = erros_por_municipio(erros)
            for h in HORIZONTES:
                pm = por_municipio.loc[h]
                linhas.append({'Municipios_treino': n, 'Sorteio': s + 1, 'h': h,
                               'Razao_MAE': pm['abs_m'].sum() / pm['abs_b'].sum()})
    curva = pd.DataFrame(linhas)

    # Ajuste erro(n) = a + b * n^(-c) sobre a média dos sorteios
    ajustes = []
    for h in HORIZONTES:
        media = curva[curva['h'] == h].groupby('Municipios_treino')['Razao_MAE'].mean()
        try:
            (a, b, c), _ = curve_fit(lambda n, a, b, c: a + b * n ** (-c), media.index.values, media.values,
                                     p0=[media.min(), 1.0, 0.5], bounds=([0, 0, 0], [2, 50, 3]), maxfev=20000)
            ajustes.append({'h': h, 'Assintota_a': a, 'b': b, 'c': c,
                            'Razao_prevista_100': a + b * 100 ** (-c), 'Razao_prevista_200': a + b * 200 ** (-c)})
        except RuntimeError:
            logging.warning(f"Ajuste da curva não convergiu para H+{h}.")
    return curva, pd.DataFrame(ajustes)


def run_experimento():
    dados = adicionar_clima(carregar('treino'))
    grupos = grupos_de_municipios(dados['cidade'].unique())
    logging.info(f"{dados['cidade'].nunique()} municípios de treino em {N_GRUPOS} grupos.")

    config = validacao_cruzada(dados, grupos)
    config.round(4).to_csv(ARQUIVO_CONFIG, index=False)
    logging.info(f"Resultado salvo em {ARQUIVO_CONFIG}.")
    print(config.round(3).to_string(index=False))

    curva, ajustes = curva_de_aprendizado(dados, grupos)
    saida = curva.merge(ajustes, on='h', how='left')
    saida.round(4).to_csv(ARQUIVO_CURVA, index=False)
    logging.info(f"Resultado salvo em {ARQUIVO_CURVA}.")
    print(curva.groupby(['h', 'Municipios_treino'])['Razao_MAE'].agg(['mean', 'min', 'max']).round(3).to_string())
    print(ajustes.round(3).to_string(index=False))


if __name__ == "__main__":
    run_experimento()
