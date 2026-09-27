"""
Sinalização de tendência do InfoDengue, usada SÓ como referência externa de comparação
(o Rt não é usado nos modelos do projeto; ver a decisão sobre o Rt no README).

O InfoDengue publica, para cada semana, o Rt (número de reprodução: quantas pessoas cada
infectado contamina) e o p_rt1 (probabilidade de o Rt ser maior que 1). Rt acima de 1
indica epidemia crescendo, e abaixo de 1, diminuindo. Os dois são estimativas da
transmissão na semana de partida t, disponíveis no mesmo momento que os casos usados
pelo modelo; não são previsões.

Três formas de transformar essa sinalização em tendência para t + H:
  - SinalRt:      regra direta; Rt > 1,1 -> sobe; Rt < 0,9 -> cai; senão, estável;
  - SinalPRt1:    regra direta; p_rt1 > 0,9 -> sobe; p_rt1 < 0,1 -> cai; senão, estável;
  - ClassificadorRt: LightGBM classificador treinado só com Rt e p_rt1 (e o nível atual de
    casos, para ele poder aprender o limite de 5 casos da regra de tendência). É o melhor
    uso possível do Rt com a mesma técnica do nosso modelo, e torna a comparação justa:
    as regras diretas não foram feitas para a nossa definição de tendência (20% e 5 casos).
As regras não produzem número de casos.
"""
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

from src.modelos.base import Modelo, tendencia_real

LIMIARES_RT = (0.9, 1.1)
LIMIARES_P_RT1 = (0.1, 0.9)
FEATURES_RT = ['rt', 'p_rt1', 'log_casos']


def _regra(valor, limites):
    inferior, superior = limites
    return np.where(valor > superior, 'sobe', np.where(valor < inferior, 'cai', 'estável'))


class SinalRt(Modelo):
    nome = 'sinal_rt'
    descricao = 'Regra do Rt do InfoDengue (> 1,1 sobe; < 0,9 cai)'

    def treinar(self, df, horizonte):
        return self

    def prever(self, df, horizonte):
        return pd.DataFrame({'previsto': np.nan, 'tendencia': _regra(df['rt'], LIMIARES_RT)}, index=df.index)


class SinalPRt1(Modelo):
    nome = 'sinal_p_rt1'
    descricao = 'Regra do p_rt1 do InfoDengue (> 0,9 sobe; < 0,1 cai)'

    def treinar(self, df, horizonte):
        return self

    def prever(self, df, horizonte):
        return pd.DataFrame({'previsto': np.nan, 'tendencia': _regra(df['p_rt1'], LIMIARES_P_RT1)}, index=df.index)


class ClassificadorRt(Modelo):
    nome = 'classificador_rt'
    descricao = 'LightGBM classificador só com Rt, p_rt1 e casos atuais'

    def treinar(self, df, horizonte):
        self.modelo = LGBMClassifier(n_estimators=300, learning_rate=0.05, random_state=42, verbose=-1)
        self.modelo.fit(df[FEATURES_RT], tendencia_real(df, horizonte))
        return self

    def prever(self, df, horizonte):
        return pd.DataFrame({'previsto': np.nan, 'tendencia': self.modelo.predict(df[FEATURES_RT])}, index=df.index)
