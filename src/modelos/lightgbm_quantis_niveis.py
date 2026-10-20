"""
LightGBM por quantis em grade (5% a 95%, de 5 em 5): a distribuição prevista dos casos em S+H.

Com muitos quantis, a curva "chance de vir menos de X casos" fica conhecida em 19 pontos; a
chance de cada nível sai dessa curva, lida nos limiares do MEM (probabilidades_niveis):
  P(vermelho) = 1 - F(limiar epidêmico), P(verde) = F(limiar pré-epidêmico), P(amarelo) = o resto.
Por padrão, mesmas variáveis e hiperparâmetros de src/modelos/lightgbm_quantis.py (que tem só 10%,
50% e 90%); 'grade' e 'features' permitem outra grade e outras variáveis (por exemplo, as do
classificador de níveis, com o clima e a distância aos limiares: FEATURES_NIVEIS).
"""
import numpy as np
from lightgbm import LGBMRegressor

from src.modelos.base import Modelo, alvo_relativo, casos_de_relativo
from src.train import FEATURES

GRADE = np.round(np.arange(0.05, 0.951, 0.05), 2)


class LightGBMQuantisNiveis(Modelo):
    nome = 'lightgbm_quantis_niveis'
    descricao = 'LightGBM por quantis em grade (5% a 95%): casos e chance de cada nível'

    def __init__(self, threads=-1, grade=GRADE, features=FEATURES):
        self.threads = threads
        self.grade = np.asarray(grade)
        self.features = list(features)

    def treinar(self, df, horizonte):
        y = alvo_relativo(df, horizonte)
        self.modelos = [LGBMRegressor(objective='quantile', alpha=q, n_estimators=300, learning_rate=0.05,
                                      random_state=42, n_jobs=self.threads, verbose=-1).fit(df[self.features], y)
                        for q in self.grade]
        return self

    def prever_quantis(self, df, horizonte):
        """Matriz (semanas x quantis da grade) com os casos previstos, em ordem crescente."""
        q = np.column_stack([casos_de_relativo(df, m.predict(df[self.features])) for m in self.modelos])
        return np.sort(q, axis=1)  # quantis estimados separadamente podem se cruzar


def distribuicao_acumulada(quantis, valor, grade=GRADE):
    """F(valor) = chance de vir menos que 'valor' casos, interpolando os quantis em escala log1p.

    Entre dois quantis, linear em log1p(casos). Abaixo do primeiro (ou acima do último), a curva
    continua com a inclinação do trecho vizinho até chegar a 0 (ou 1).
    """
    x = np.log1p(np.asarray(quantis, dtype=float))
    v = np.log1p(np.asarray(valor, dtype=float))[:, None]
    n = x.shape[1]
    i = (x < v).sum(axis=1)  # quantos quantis ficam abaixo do valor
    linhas = np.arange(len(x))
    esq, dir_ = np.clip(i - 1, 0, n - 2), np.clip(i, 1, n - 1)
    x0, x1 = x[linhas, esq], x[linhas, dir_]
    a0, a1 = grade[esq], grade[dir_]
    largura = x1 - x0
    with np.errstate(divide='ignore', invalid='ignore'):
        f = a0 + (v[:, 0] - x0) / largura * (a1 - a0)
    # Quantis repetidos na ponta (largura zero, por exemplo todos em 0 casos): degrau no ponto
    f = np.where(largura > 0, f, np.where(v[:, 0] > x0, 1.0, 0.0))
    return np.clip(f, 0, 1)


def probabilidades_niveis(quantis, limiar_amarelo, limiar_vermelho, grade=GRADE):
    """Matriz (semanas x 3) com a chance de verde, amarelo e vermelho (casos >= limiar sobe de nível)."""
    f_amarelo = distribuicao_acumulada(quantis, limiar_amarelo, grade)
    f_vermelho = np.maximum(distribuicao_acumulada(quantis, limiar_vermelho, grade), f_amarelo)
    return np.column_stack([f_amarelo, f_vermelho - f_amarelo, 1 - f_vermelho])
