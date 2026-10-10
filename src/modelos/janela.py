"""
Janela das últimas SEMANAS_JANELA semanas, para os modelos que olham mais longe que as
variáveis comuns (variação dos casos em relação a 1-4 semanas atrás e clima de S-1 a S-4).

Acrescenta, por município:
  - var_log_k (k = 1 a SEMANAS_JANELA - 1): log_casos(S) - log_casos(S-k), como os var_log_1 a 4
    do pré-processamento;
  - <variável>_s<k> (k = 1 a SEMANAS_JANELA): clima da semana S-k, como os _s1 a _s4.
Só usa semanas anteriores a S (para o clima, anteriores a S-1), então não há vazamento.
"""
import numpy as np

from src.modelos.lightgbm_classificador_clima import VARIAVEIS_CLIMA

SEMANAS_JANELA = 12


def colunas_variacao(semanas=SEMANAS_JANELA):
    return [f'var_log_{k}' for k in range(1, semanas)]


def colunas_clima_janela(semanas=SEMANAS_JANELA):
    return [f'{v}_s{k}' for k in range(1, semanas + 1) for v in VARIAVEIS_CLIMA]


def adicionar_janela(df, semanas=SEMANAS_JANELA):
    df = df.sort_values(['cidade', 'data_iniSE']).copy()
    por_cidade = df.groupby('cidade', sort=False)
    for k in range(1, semanas):
        df[f'var_log_{k}'] = df['log_casos'] - np.log1p(por_cidade['casos_est'].shift(k))
    for v in VARIAVEIS_CLIMA:
        for k in range(1, semanas + 1):
            df[f'{v}_s{k}'] = por_cidade[v].shift(k)
    return df
