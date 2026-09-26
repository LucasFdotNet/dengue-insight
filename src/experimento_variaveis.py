"""
Experimento: retirar o Rt e incluir variáveis climáticas no modelo.

Motivação (ver "Decisões de Projeto" no README): o Rt é calculado pelo InfoDengue a
partir da própria série de casos. Tirá-lo deixa o modelo baseado só em casos (nowcast)
e, opcionalmente, clima, e permite comparar o modelo com a sinalização de tendência
do próprio InfoDengue como uma referência independente.

Configurações comparadas (mesma validação walk-forward com retreino mensal do train.py):
  A. modelo anterior: casos + Rt + semana do ano, sem clima;
  B. sem Rt: casos + semana do ano;
  C. sem Rt + clima mínimo: chuva acumulada e temperatura média das 8 semanas anteriores;
  D. sem Rt + clima compacto: chuva de 4 e 8 semanas, temperatura média de 4 e 8 semanas
     e umidade média de 4 semanas;
  E. sem Rt + chuva de 4 e 12 semanas e temperatura média de 8 semanas.
O clima usa só semanas anteriores à semana de partida (o ERA5 chega com ~6 dias de atraso).

Referências externas de tendência (sinalização do InfoDengue na semana de partida):
  - p_rt1 (probabilidade de Rt > 1): > 0,9 -> sobe; < 0,1 -> cai; senão, estável;
  - Rt: > 1,1 -> sobe; < 0,9 -> cai; senão, estável.

Saída: reports/experimento_variaveis.csv
"""
import logging

import numpy as np
import pandas as pd

from src.train import (FEATURES, avaliar_walk_forward, carregar, classificar_tendencia,
                       resumir, resumir_tendencia)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_SAIDA = 'reports/experimento_variaveis.csv'

# O modelo final (FEATURES) não usa Rt; a configuração A reproduz o modelo anterior, com Rt
SEM_RT = FEATURES
COM_RT = [f for f in FEATURES if f != 'semana_ano'] + ['rt_lag_1', 'semana_ano']
CONFIGURACOES = {
    'A. Com Rt, sem clima (anterior)': COM_RT,
    'B. Sem Rt, sem clima': SEM_RT,
    'C. Sem Rt + clima mínimo': SEM_RT + ['chuva_8', 'tmed_8'],
    'D. Sem Rt + clima compacto': SEM_RT + ['chuva_4', 'chuva_8', 'tmed_4', 'tmed_8', 'umid_4'],
    'E. Sem Rt + chuva 4 e 12 semanas e temperatura 8 semanas': SEM_RT + ['chuva_4', 'chuva_12', 'tmed_8'],
}


def adicionar_clima(df):
    """Agregados climáticos das semanas anteriores à semana de partida (shift de 1)."""
    df = df.sort_values(['cidade', 'data_iniSE']).copy()
    por_cidade = df.groupby('cidade')
    for janela in [4, 8, 12]:
        df[f'chuva_{janela}'] = por_cidade['precipitacao'].transform(lambda s: s.shift(1).rolling(janela).sum())
    for janela in [4, 8]:
        df[f'tmed_{janela}'] = por_cidade['tmed'].transform(lambda s: s.shift(1).rolling(janela).mean())
    df['umid_4'] = por_cidade['umidade'].transform(lambda s: s.shift(1).rolling(4).mean())
    return df


def tendencia_infodengue(erros, dados):
    """Acerto de tendência das regras baseadas no Rt e no p_rt1 do InfoDengue."""
    partida = erros[['Grupo', 'Horizonte', 'cidade', 'data_alvo', 'h', 'real', 'atual']].copy()
    partida['data_iniSE'] = partida['data_alvo'] - pd.to_timedelta(partida['h'] * 7, unit='D')
    partida = partida.merge(dados[['cidade', 'data_iniSE', 'rt', 'p_rt1']], on=['cidade', 'data_iniSE'], how='left')
    real = classificar_tendencia(partida['real'], partida['atual'])
    regras = {
        'Ref. InfoDengue: p_rt1': np.where(partida['p_rt1'] > 0.9, 'sobe', np.where(partida['p_rt1'] < 0.1, 'cai', 'estável')),
        'Ref. InfoDengue: Rt': np.where(partida['rt'] > 1.1, 'sobe', np.where(partida['rt'] < 0.9, 'cai', 'estável')),
    }
    linhas = []
    for nome, previsto in regras.items():
        df = partida[['Grupo', 'Horizonte']].assign(real=real, previsto=previsto)
        for (grupo, horizonte), g in df.groupby(['Grupo', 'Horizonte'], sort=False):
            subiu, previu = g['real'] == 'sobe', g['previsto'] == 'sobe'
            oposto = ((g['real'] == 'sobe') & (g['previsto'] == 'cai')) | ((g['real'] == 'cai') & (g['previsto'] == 'sobe'))
            linhas.append({
                'Configuracao': nome, 'Grupo': grupo, 'Horizonte': horizonte,
                'Acerto_tendencia': (g['real'] == g['previsto']).mean(),
                'Acerto_sempre_estavel': (g['real'] == 'estável').mean(),
                'Subidas_detectadas': (g.loc[subiu, 'previsto'] == 'sobe').mean(),
                'Alarmes_subida_corretos': (g.loc[previu, 'real'] == 'sobe').mean(),
                'Sentido_oposto': oposto.mean(),
            })
    return pd.DataFrame(linhas)


def run_experimento():
    treino, validacao = adicionar_clima(carregar('treino')), adicionar_clima(carregar('validacao'))
    todos = pd.concat([treino, validacao], ignore_index=True)

    resultados = []
    erros_referencia = None
    for nome, features in CONFIGURACOES.items():
        logging.info(f"Configuração {nome}...")
        erros = avaliar_walk_forward(treino, validacao, features=features)
        if erros_referencia is None:
            erros_referencia = erros
        mae = resumir(erros, ['Grupo', 'Horizonte'])[['Grupo', 'Horizonte', 'Razao_MAE']]
        tend = resumir_tendencia(erros).rename(columns={'Acerto_modelo': 'Acerto_tendencia'})
        tend = tend[['Grupo', 'Horizonte', 'Acerto_tendencia', 'Acerto_sempre_estavel', 'Subidas_detectadas',
                     'Alarmes_subida_corretos', 'Sentido_oposto']]
        resultados.append(mae.merge(tend, on=['Grupo', 'Horizonte']).assign(Configuracao=nome))

    resultados.append(tendencia_infodengue(erros_referencia, todos))
    tabela = pd.concat(resultados, ignore_index=True)
    colunas = ['Configuracao', 'Grupo', 'Horizonte', 'Razao_MAE', 'Acerto_tendencia', 'Acerto_sempre_estavel',
               'Subidas_detectadas', 'Alarmes_subida_corretos', 'Sentido_oposto']
    tabela = tabela[colunas].round(3)
    tabela.to_csv(ARQUIVO_SAIDA, index=False)
    logging.info(f"Resultado salvo em {ARQUIVO_SAIDA}.")
    print(tabela.to_string(index=False))


if __name__ == "__main__":
    run_experimento()
