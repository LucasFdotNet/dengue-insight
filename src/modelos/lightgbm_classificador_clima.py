"""
LightGBM classificador com clima das semanas anteriores à semana atual S.

Mesmo modelo de lightgbm_classificador.py, com o clima semana a semana (temperatura
média, chuva total e umidade média) de S-1 a S-4 ou de S-1 a S-5. As colunas são criadas
por experimento_clima_semanal.adicionar_clima (nome '<variável>_s<k>'). O clima da
semana S não é usado, porque o ERA5 chega com cerca de 6 dias de atraso.
"""
from src.modelos.lightgbm_classificador import LightGBMClassificador
from src.train import FEATURES

VARIAVEIS_CLIMA = ['tmed', 'precipitacao', 'umidade']


def colunas_clima(ultima_semana):
    return [f'{v}_s{k}' for k in range(1, ultima_semana + 1) for v in VARIAVEIS_CLIMA]


class ClassificadorClimaS1S4(LightGBMClassificador):
    nome = 'lightgbm_classificador_clima_s1_s4'
    descricao = 'LightGBM classificador com clima de S-1 a S-4'
    features = FEATURES + colunas_clima(4)


class ClassificadorClimaS1S5(LightGBMClassificador):
    nome = 'lightgbm_classificador_clima_s1_s5'
    descricao = 'LightGBM classificador com clima de S-1 a S-5'
    features = FEATURES + colunas_clima(5)
