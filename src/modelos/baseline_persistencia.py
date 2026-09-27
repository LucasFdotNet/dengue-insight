"""
Baseline de persistência: prevê que daqui a H semanas haverá o mesmo número de casos
de hoje. Na tendência, equivale a dizer sempre "estável".

É a referência mínima: um modelo só é útil se for melhor que isso.
"""
from src.modelos.base import Modelo


class BaselinePersistencia(Modelo):
    nome = 'baseline_persistencia'
    descricao = 'Baseline de persistência (repete os casos atuais; tendência sempre "estável")'

    def treinar(self, df, horizonte):
        return self

    def _prever_casos(self, df, horizonte):
        return df['casos_est'].values
