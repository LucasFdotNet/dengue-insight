"""
LightGBM de estado: probabilidade de o município estar no nível alto daqui a H semanas.

Mesmo LightGBM e mesmas variáveis do classificador de tendência em produção (casos atuais,
variação em relação a 1-4 semanas atrás, semana do ano e clima de S-1 a S-4), mais a
distância da semana atual ao limiar do município (razao_limiar, src/estados.py), que diz
o quanto falta para entrar no nível alto ou para sair dele. O alvo é alto_h<H>.
"""
import numpy as np
from lightgbm import LGBMClassifier

from src.modelos.lightgbm_classificador_clima import colunas_clima
from src.train import FEATURES

FEATURES_ESTADO = FEATURES + colunas_clima(4) + ['razao_limiar']


class EstadoLightGBM:
    nome = 'lightgbm_estado'
    descricao = 'LightGBM: probabilidade de nível alto em S+H'
    features = FEATURES_ESTADO
    parametros = {'n_estimators': 300, 'learning_rate': 0.05, 'num_leaves': 31, 'min_child_samples': 20}

    def __init__(self, semente=42, threads=-1):
        self.semente = semente
        self.threads = threads

    def treinar(self, df, horizonte):
        self.modelo = LGBMClassifier(**self.parametros, random_state=self.semente, n_jobs=self.threads, verbose=-1)
        self.modelo.fit(df[self.features], df[f'alto_h{horizonte}'].astype(int))
        return self

    def prever(self, df, horizonte):
        """Probabilidade de nível alto em S+H (array)."""
        p = self.modelo.predict_proba(df[self.features])
        return p[:, list(self.modelo.classes_).index(1)] if 1 in self.modelo.classes_ else np.zeros(len(df))
