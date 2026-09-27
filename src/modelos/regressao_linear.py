"""
Regressão linear regularizada (Ridge) sobre o alvo relativo.

Mesmas informações do LightGBM (casos atuais em log, variação em relação a 1-4 semanas
atrás e semana do ano), com a semana do ano codificada como seno e cosseno. Serve para
testar se a complexidade do LightGBM (relações não lineares) faz diferença: se a
regressão linear empatar, o modelo mais simples seria preferível.
"""
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.modelos.base import Modelo, alvo_relativo, casos_de_relativo, features_ciclicas


class RegressaoLinear(Modelo):
    nome = 'regressao_linear'
    descricao = 'Regressão linear Ridge (alvo relativo)'

    def __init__(self, alpha=1.0):
        self.alpha = alpha

    def treinar(self, df, horizonte):
        self.modelo = make_pipeline(StandardScaler(), Ridge(alpha=self.alpha))
        self.modelo.fit(features_ciclicas(df), alvo_relativo(df, horizonte))
        return self

    def prever_relativo(self, df, horizonte):
        return self.modelo.predict(features_ciclicas(df))

    def _prever_casos(self, df, horizonte):
        return casos_de_relativo(df, self.prever_relativo(df, horizonte))
