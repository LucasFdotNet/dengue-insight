"""
Ensemble (média de modelos): combina a regressão linear, a binomial negativa e o
LightGBM atual, tirando a média das variações previstas em escala log (equivale à média
geométrica dos casos previstos).

Em previsão, combinar modelos diferentes costuma superar cada um isoladamente, porque os
erros de um compensam em parte os erros dos outros.
"""
import numpy as np

from src.modelos.base import Modelo, casos_de_relativo
from src.modelos.binomial_negativa import BinomialNegativa
from src.modelos.lightgbm_atual import LightGBMAtual
from src.modelos.regressao_linear import RegressaoLinear


class Ensemble(Modelo):
    nome = 'ensemble'
    descricao = 'Média da regressão linear, binomial negativa e LightGBM atual'

    def treinar(self, df, horizonte):
        self.componentes = [RegressaoLinear().treinar(df, horizonte),
                            BinomialNegativa().treinar(df, horizonte),
                            LightGBMAtual().treinar(df, horizonte)]
        return self

    def _prever_casos(self, df, horizonte):
        relativos = [np.log1p(np.maximum(m._prever_casos(df, horizonte), 0)) - df['log_casos']
                     for m in self.componentes]
        return casos_de_relativo(df, np.mean(relativos, axis=0))
