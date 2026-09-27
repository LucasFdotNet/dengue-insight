"""
LightGBM classificador: prevê a tendência (sobe, estável ou cai) diretamente, em vez de
prever o número de casos e depois classificar.

Como o objetivo do projeto passou a ser acertar a tendência, este modelo testa se vale a
pena treinar diretamente para essa pergunta. Ele não produz número de casos, então não
entra nas métricas de erro em casos.
"""
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

from src.modelos.base import Modelo, tendencia_real
from src.train import FEATURES


class LightGBMClassificador(Modelo):
    nome = 'lightgbm_classificador'
    descricao = 'LightGBM classificador (prevê a tendência diretamente)'

    def treinar(self, df, horizonte):
        self.modelo = LGBMClassifier(n_estimators=300, learning_rate=0.05, random_state=42, verbose=-1)
        self.modelo.fit(df[FEATURES], tendencia_real(df, horizonte))
        return self

    def prever(self, df, horizonte):
        return pd.DataFrame({'previsto': np.nan, 'tendencia': self.modelo.predict(df[FEATURES])}, index=df.index)
