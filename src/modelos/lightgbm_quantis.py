"""
LightGBM por quantis: três modelos, para os quantis de 10%, 50% e 90% do alvo relativo.

A previsão central (e a tendência) vem da mediana; os quantis de 10% e 90% formam um
intervalo de previsão de 80% ("entre X e Y casos"). A avaliação mede a cobertura: em que
fração das semanas o valor real ficou dentro do intervalo (o ideal é perto de 80%).
"""
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor

from src.modelos.base import Modelo, alvo_relativo, casos_de_relativo
from src.train import FEATURES, classificar_tendencia

QUANTIS = {'inferior': 0.10, 'previsto': 0.50, 'superior': 0.90}


class LightGBMQuantis(Modelo):
    nome = 'lightgbm_quantis'
    descricao = 'LightGBM por quantis (mediana e intervalo de 80%)'

    def treinar(self, df, horizonte):
        y = alvo_relativo(df, horizonte)
        self.modelos = {
            chave: LGBMRegressor(objective='quantile', alpha=q, n_estimators=300, learning_rate=0.05,
                                 random_state=42, verbose=-1).fit(df[FEATURES], y)
            for chave, q in QUANTIS.items()
        }
        return self

    def prever(self, df, horizonte):
        saida = pd.DataFrame({chave: casos_de_relativo(df, m.predict(df[FEATURES]))
                              for chave, m in self.modelos.items()}, index=df.index)
        # Quantis estimados separadamente podem se cruzar; ordena para manter inferior <= mediana <= superior
        ordenado = pd.DataFrame(np.sort(saida[['inferior', 'previsto', 'superior']].values, axis=1),
                                columns=['inferior', 'previsto', 'superior'], index=df.index)
        ordenado['tendencia'] = classificar_tendencia(ordenado['previsto'], df['casos_est'])
        return ordenado

