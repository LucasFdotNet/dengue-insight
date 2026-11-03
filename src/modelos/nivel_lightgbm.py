"""
LightGBM de níveis: probabilidade de cada nível (verde, amarelo, vermelho) em S+H.

Mesmas variáveis do modelo de estado (src/modelos/estado_lightgbm.py), com a distância da
semana atual a cada um dos dois limiares (src/estados.adicionar_niveis). O alvo é faixa_h<H>.
"""
import numpy as np
from lightgbm import LGBMClassifier

from src.modelos.lightgbm_classificador_clima import colunas_clima
from src.train import FEATURES

FEATURES_NIVEIS = FEATURES + colunas_clima(4) + ['razao_amarelo', 'razao_vermelho']


class NivelLightGBM:
    nome = 'lightgbm_niveis'
    descricao = 'LightGBM: probabilidade de cada nível em S+H'
    features = FEATURES_NIVEIS
    parametros = {'n_estimators': 300, 'learning_rate': 0.05, 'num_leaves': 31, 'min_child_samples': 20}

    def __init__(self, semente=42, threads=-1):
        self.semente = semente
        self.threads = threads

    def treinar(self, df, horizonte):
        self.modelo = LGBMClassifier(**self.parametros, random_state=self.semente, n_jobs=self.threads, verbose=-1)
        self.modelo.fit(df[self.features], df[f'faixa_h{horizonte}'].astype(int))
        return self

    def prever(self, df, horizonte):
        """Matriz (semanas x 3) com a probabilidade de verde, amarelo e vermelho em S+H."""
        p = self.modelo.predict_proba(df[self.features])
        saida = np.zeros((len(df), 3))
        for j, classe in enumerate(self.modelo.classes_):
            saida[:, int(classe)] = p[:, j]
        return saida
