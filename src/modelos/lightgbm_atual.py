"""
LightGBM atual: o modelo usado pelo projeto (src/train.py), com os mesmos
hiperparâmetros fixos (300 árvores, taxa de aprendizado 0,05) e o alvo relativo.
"""
from lightgbm import LGBMRegressor

from src.modelos.base import Modelo, alvo_relativo, casos_de_relativo
from src.train import FEATURES


class LightGBMAtual(Modelo):
    nome = 'lightgbm_atual'
    descricao = 'LightGBM atual (hiperparâmetros fixos)'
    parametros = dict(n_estimators=300, learning_rate=0.05)

    def treinar(self, df, horizonte):
        self.modelo = LGBMRegressor(**self.parametros, random_state=42, verbose=-1)
        self.modelo.fit(df[FEATURES], alvo_relativo(df, horizonte))
        return self

    def prever_relativo(self, df, horizonte):
        return self.modelo.predict(df[FEATURES])

    def _prever_casos(self, df, horizonte):
        return casos_de_relativo(df, self.prever_relativo(df, horizonte))
