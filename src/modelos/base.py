"""
Interface comum dos modelos comparados em experimento_modelos.py.

Cada modelo é treinado para um horizonte H (1 a 4 semanas) e, para cada semana de
partida t, prevê o número de casos em t + H e a tendência (sobe, estável ou cai) em
relação à semana t. A tendência segue a mesma regra do resto do projeto
(train.classificar_tendencia: subida ou queda quando a variação passa de 20% e de 5 casos).

Para implementar um modelo novo, basta herdar de Modelo e implementar treinar() e
_prever_casos() (ou prever(), se o modelo prevê a tendência diretamente).
"""
import numpy as np
import pandas as pd

from src.train import FEATURES, classificar_tendencia


class Modelo:
    nome = 'modelo'
    descricao = ''

    def treinar(self, df, horizonte):
        raise NotImplementedError

    def _prever_casos(self, df, horizonte):
        """Número de casos previsto para t + H (array)."""
        raise NotImplementedError

    def prever(self, df, horizonte):
        """DataFrame com 'previsto' (casos), 'tendencia' e, se houver, 'inferior'/'superior' (intervalo)."""
        previsto = np.maximum(np.asarray(self._prever_casos(df, horizonte), dtype=float), 0)
        return pd.DataFrame({
            'previsto': previsto,
            'tendencia': classificar_tendencia(previsto, df['casos_est']),
        }, index=df.index)


# --------------------------------------------------------------- utilitários comuns

def alvo(df, horizonte):
    return df[f'target_h{horizonte}']


def alvo_relativo(df, horizonte):
    """Variação em escala log: log1p(casos em t+H) - log1p(casos em t)."""
    return np.log1p(alvo(df, horizonte)) - df['log_casos']


def casos_de_relativo(df, relativo):
    return np.maximum(np.expm1(df['log_casos'] + relativo), 0)


def tendencia_real(df, horizonte):
    return classificar_tendencia(alvo(df, horizonte), df['casos_est'])


def features_ciclicas(df):
    """FEATURES com a semana do ano como seno e cosseno (para modelos lineares, em que a
    semana 52 e a semana 1 precisam ficar próximas)."""
    x = df[[f for f in FEATURES if f != 'semana_ano']].copy()
    angulo = 2 * np.pi * df['semana_ano'] / 52.18
    x['semana_sen'] = np.sin(angulo)
    x['semana_cos'] = np.cos(angulo)
    return x
