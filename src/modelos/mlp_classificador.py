"""
Rede neural MLP (perceptron multicamadas) classificadora com clima de S-1 a S-4.

Mesmas informações do classificador em produção, com a semana do ano como seno e
cosseno (para a semana 52 ficar perto da semana 1). A rede exige entradas completas e na
mesma escala: os valores faltantes do clima recebem a média do treino, e todas as
variáveis são padronizadas com média e desvio do treino. Usa 10% do treino para parar
o treinamento quando a rede deixa de melhorar (early stopping).
"""
from sklearn.impute import SimpleImputer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.modelos.base import Classificador, features_ciclicas
from src.modelos.lightgbm_classificador_clima import colunas_clima


class MLPClassificador(Classificador):
    nome = 'mlp_classificador'
    descricao = 'Rede neural MLP classificadora com clima de S-1 a S-4'
    parametros = {'hidden_layer_sizes': (64, 32), 'alpha': 1e-4, 'learning_rate_init': 1e-3, 'batch_size': 512}

    def _x(self, df):
        x = features_ciclicas(df)
        return x.join(df[colunas_clima(4)])

    def _novo_modelo(self):
        rede = MLPClassifier(**self.parametros, max_iter=200, early_stopping=True,
                             validation_fraction=0.1, n_iter_no_change=10, random_state=self.semente)
        return make_pipeline(SimpleImputer(), StandardScaler(), rede)
