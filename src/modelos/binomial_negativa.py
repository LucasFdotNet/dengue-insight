"""
Regressão binomial negativa (GLM), o modelo clássico da epidemiologia para contagens.

Prevê diretamente o número de casos em t + H. Os casos atuais entram como "offset"
(log(1 + casos em t)), de modo que os coeficientes descrevem a variação em relação ao
nível atual, como o alvo relativo dos outros modelos. A binomial negativa, ao contrário
da Poisson, admite variância maior que a média, que é o caso das séries de dengue.

O parâmetro de dispersão (alpha) é estimado a cada treino por máxima verossimilhança
(statsmodels.discrete.NegativeBinomial).
"""
import logging
import warnings

import numpy as np
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import NegativeBinomial

from src.modelos.base import Modelo, alvo, features_ciclicas


class BinomialNegativa(Modelo):
    nome = 'binomial_negativa'
    descricao = 'Regressão binomial negativa (GLM para contagens)'

    def _matriz(self, df):
        x = features_ciclicas(df)
        x = (x - self.media) / self.desvio
        return sm.add_constant(x, has_constant='add')

    def treinar(self, df, horizonte):
        x = features_ciclicas(df)
        self.media, self.desvio = x.mean(), x.std().replace(0, 1)
        y = np.round(alvo(df, horizonte)).clip(lower=0)
        offset = np.log1p(df['casos_est'])
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            modelo = NegativeBinomial(y, self._matriz(df), offset=offset)
            self.resultado = modelo.fit(method='bfgs', maxiter=200, disp=False)
            if not self.resultado.mle_retvals.get('converged', True):
                logging.warning(f"Binomial negativa H+{horizonte}: otimização não convergiu.")
        return self

    def _prever_casos(self, df, horizonte):
        return self.resultado.predict(self._matriz(df), offset=np.log1p(df['casos_est']))
