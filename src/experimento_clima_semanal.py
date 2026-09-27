"""
Experimento: clima das semanas anteriores à semana atual (S), com a base nacional.

Motivação: o ciclo de ovo a mosquito adulto leva de 7 a 10 dias, e a atividade do
mosquito depende das condições climáticas. Com os municípios de treino de várias
regiões do país (climas e sazonalidades diferentes), o modelo tem mais variação de
clima para aprender do que com os 13 municípios de SP.

O clima da própria semana S não é usado: o ERA5 chega com cerca de 6 dias de atraso,
então S ainda não está completa no momento da previsão.

Configurações (todas sem Rt, mesma validação walk-forward com retreino mensal do train.py):
  - sem clima, treinado só com os 13 municípios de treino de SP (base anterior);
  - sem clima, treinado com todos os municípios de treino (modelo atual; eram 63 quando o
    experimento foi criado, e o resultado salvo é dessa base);
  - clima semana a semana de S-1 a S-2, de S-1 a S-4 e de S-1 a S-5;
  - média do clima de S-1 a S-8 (chuva: total das 8 semanas).
Variáveis climáticas: temperatura média, chuva total e umidade média da semana (o
conjunto "essencial", que foi o melhor no teste anterior com os municípios de SP).

Os resultados são separados por grupo (treino ou validação espacial) e por abrangência
(SP ou Brasil fora de SP). O modelo treinado só com SP é avaliado apenas nos municípios
de SP, para comparar com o modelo nacional nas mesmas semanas.

Com a opção --sem-clima, roda só as duas configurações sem clima (treino só SP e
treino nacional), que não dependem da ingestão de clima.

Saída: reports/experimento_clima_semanal.csv
"""
import logging
import sys

import pandas as pd

from src.cidades import CIDADES
from src.train import FEATURES, avaliar_walk_forward, carregar, resumir, resumir_tendencia

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_SAIDA = 'reports/experimento_clima_semanal.csv'

VARIAVEIS = ['tmed', 'precipitacao', 'umidade']
SEMANAS = {
    'S-1 a S-2': [1, 2],
    'S-1 a S-4': [1, 2, 3, 4],
    'S-1 a S-5': [1, 2, 3, 4, 5],
}
JANELA_MEDIA = 8

SO_SP = 'Sem clima, treino só SP (13 municípios)'


def adicionar_clima(df):
    """Clima de cada semana anterior ('<variável>_s<k>' = valor da semana S-k) e médias de S-1 a S-8."""
    df = df.sort_values(['cidade', 'data_iniSE']).copy()
    por_cidade = df.groupby('cidade')
    for variavel in VARIAVEIS:
        for k in range(1, max(max(s) for s in SEMANAS.values()) + 1):
            df[f'{variavel}_s{k}'] = por_cidade[variavel].shift(k)
        agregado = 'sum' if variavel == 'precipitacao' else 'mean'
        df[f'{variavel}_media_s1_s{JANELA_MEDIA}'] = por_cidade[variavel].transform(
            lambda s: s.shift(1).rolling(JANELA_MEDIA).agg(agregado))
    return df


def configuracoes():
    config = {'Sem clima (modelo atual, treino nacional)': FEATURES}
    for nome, semanas in SEMANAS.items():
        config[f'Clima {nome}'] = FEATURES + [f'{v}_s{k}' for k in semanas for v in VARIAVEIS]
    config[f'Clima: média de S-1 a S-{JANELA_MEDIA}'] = FEATURES + [f'{v}_media_s1_s{JANELA_MEDIA}' for v in VARIAVEIS]
    return config


def resumir_por_abrangencia(erros, nome):
    erros = erros.assign(Abrangencia=erros['cidade'].map(lambda k: 'SP' if CIDADES[k]['uf'] == 'SP' else 'Brasil fora de SP'))
    linhas = []
    for abrangencia, e in erros.groupby('Abrangencia'):
        mae = resumir(e, ['Grupo', 'Horizonte'])[['Grupo', 'Horizonte', 'Semanas', 'Razao_MAE']]
        tend = resumir_tendencia(e).rename(columns={'Acerto_modelo': 'Acerto_tendencia'})
        tend = tend[['Grupo', 'Horizonte', 'Acerto_tendencia', 'Acerto_sempre_estavel', 'Subidas_detectadas',
                     'Alarmes_subida_corretos', 'Sentido_oposto']]
        linhas.append(mae.merge(tend, on=['Grupo', 'Horizonte']).assign(Configuracao=nome, Abrangencia=abrangencia))
    return pd.concat(linhas, ignore_index=True)


def run_experimento(sem_clima=False):
    treino, validacao = adicionar_clima(carregar('treino')), adicionar_clima(carregar('validacao'))
    e_sp = lambda df: df['cidade'].map(lambda k: CIDADES[k]['uf'] == 'SP')

    resultados = []
    logging.info(f"Configuração {SO_SP}...")
    erros = avaliar_walk_forward(treino[e_sp(treino)], validacao[e_sp(validacao)], features=FEATURES)
    resultados.append(resumir_por_abrangencia(erros, SO_SP))

    config = configuracoes()
    if sem_clima:
        config = {nome: features for nome, features in config.items() if features == FEATURES}
    for nome, features in config.items():
        logging.info(f"Configuração {nome} ({len(features)} variáveis)...")
        erros = avaliar_walk_forward(treino, validacao, features=features)
        resultados.append(resumir_por_abrangencia(erros, nome))

    tabela = pd.concat(resultados, ignore_index=True)
    colunas = ['Configuracao', 'Abrangencia', 'Grupo', 'Horizonte', 'Semanas', 'Razao_MAE', 'Acerto_tendencia',
               'Acerto_sempre_estavel', 'Subidas_detectadas', 'Alarmes_subida_corretos', 'Sentido_oposto']
    tabela = tabela[colunas].round(3)
    tabela.to_csv(ARQUIVO_SAIDA, index=False)
    logging.info(f"Resultado salvo em {ARQUIVO_SAIDA}.")
    print(tabela.to_string(index=False))


if __name__ == "__main__":
    run_experimento(sem_clima='--sem-clima' in sys.argv)
