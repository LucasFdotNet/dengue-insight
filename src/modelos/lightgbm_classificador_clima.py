"""
LightGBM classificador com clima das semanas anteriores à semana atual S.

Mesmo modelo de lightgbm_classificador.py, com o clima semana a semana (temperatura
média, chuva total e umidade média) de S-1 a S-4 ou de S-1 a S-5. As colunas são criadas
por experimento_clima_semanal.adicionar_clima (nome '<variável>_s<k>'). O clima da
semana S não é usado, porque o ERA5 chega com cerca de 6 dias de atraso.

Variantes usadas em experimento_classificadores.py:
  - peso igual para as três tendências (class_weight='balanced'): a métrica principal é o
    acerto balanceado, e as subidas e quedas são mais raras que as semanas estáveis;
  - janela de 12 semanas (variação dos casos e clima), a mesma informação que a LSTM recebe,
    para separar o efeito do modelo do efeito de olhar mais semanas para trás.
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


class ClassificadorClimaBalanceado(ClassificadorClimaS1S4):
    nome = 'lightgbm_classificador_clima_balanceado'
    descricao = 'LightGBM classificador com clima de S-1 a S-4 e peso igual para as três tendências'
    peso_classes = 'balanced'


class ClassificadorClimaJanela12(LightGBMClassificador):
    nome = 'lightgbm_classificador_janela12'
    descricao = 'LightGBM classificador com janela de 12 semanas (variação dos casos e clima)'

    @property
    def features(self):
        # Import tardio: janela.py importa VARIAVEIS_CLIMA deste módulo
        from src.modelos.janela import colunas_clima_janela, colunas_variacao
        return ['log_casos', 'semana_ano'] + colunas_variacao() + colunas_clima_janela()
