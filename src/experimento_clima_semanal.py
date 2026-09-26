"""
Experimento: clima de semanas específicas antes da semana atual (S).

Motivação: o ciclo de ovo a mosquito adulto leva de 7 a 10 dias, e a atividade do
mosquito depende das condições climáticas. Em vez dos agregados de várias semanas
testados em experimento_variaveis.py, este experimento usa o clima semana a semana,
nas defasagens indicadas. O clima da própria semana S não é usado: o ERA5 chega com
cerca de 6 dias de atraso, então S ainda não está completa no momento da previsão.

Configurações (todas sem Rt, mesma validação walk-forward com retreino mensal do train.py):
  B. sem clima (modelo atual), como referência;
  clima de S-1 e S-2; clima de S-1 e S-3; clima de S-1, S-2 e S-3.
Cada combinação de semanas é testada com dois conjuntos de variáveis:
  completo: temperatura mínima, média e máxima, chuva total e umidade média da semana;
  essencial: temperatura média, chuva total e umidade média da semana.

Saída: reports/experimento_clima_semanal.csv
"""
import logging

import pandas as pd

from src.train import FEATURES, avaliar_walk_forward, carregar, resumir, resumir_tendencia

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_SAIDA = 'reports/experimento_clima_semanal.csv'

VARIAVEIS = {
    'completo': ['tmin', 'tmed', 'tmax', 'precipitacao', 'umidade'],
    'essencial': ['tmed', 'precipitacao', 'umidade'],
}
SEMANAS = {
    'S-1 e S-2': [1, 2],
    'S-1 e S-3': [1, 3],
    'S-1, S-2 e S-3': [1, 2, 3],
}


def adicionar_clima_semanal(df):
    """Clima de cada semana anterior, como colunas '<variável>_s<k>' (valor da semana S-k)."""
    df = df.sort_values(['cidade', 'data_iniSE']).copy()
    por_cidade = df.groupby('cidade')
    for variavel in VARIAVEIS['completo']:
        for k in [1, 2, 3]:
            df[f'{variavel}_s{k}'] = por_cidade[variavel].shift(k)
    return df


def configuracoes():
    config = {'B. Sem clima (modelo atual)': FEATURES}
    for nome_semanas, semanas in SEMANAS.items():
        for nome_variaveis, variaveis in VARIAVEIS.items():
            clima = [f'{v}_s{k}' for k in semanas for v in variaveis]
            config[f'Clima {nome_semanas} ({nome_variaveis})'] = FEATURES + clima
    return config


def run_experimento():
    treino = adicionar_clima_semanal(carregar('treino'))
    validacao = adicionar_clima_semanal(carregar('validacao'))

    resultados = []
    for nome, features in configuracoes().items():
        logging.info(f"Configuração {nome} ({len(features)} variáveis)...")
        erros = avaliar_walk_forward(treino, validacao, features=features)
        mae = resumir(erros, ['Grupo', 'Horizonte'])[['Grupo', 'Horizonte', 'Razao_MAE']]
        tend = resumir_tendencia(erros).rename(columns={'Acerto_modelo': 'Acerto_tendencia'})
        tend = tend[['Grupo', 'Horizonte', 'Acerto_tendencia', 'Subidas_detectadas',
                     'Alarmes_subida_corretos', 'Sentido_oposto']]
        resultados.append(mae.merge(tend, on=['Grupo', 'Horizonte']).assign(Configuracao=nome))

    tabela = pd.concat(resultados, ignore_index=True)
    colunas = ['Configuracao', 'Grupo', 'Horizonte', 'Razao_MAE', 'Acerto_tendencia',
               'Subidas_detectadas', 'Alarmes_subida_corretos', 'Sentido_oposto']
    tabela = tabela[colunas].round(3)
    tabela.to_csv(ARQUIVO_SAIDA, index=False)
    logging.info(f"Resultado salvo em {ARQUIVO_SAIDA}.")
    print(tabela.to_string(index=False))


if __name__ == "__main__":
    run_experimento()
