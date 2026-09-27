"""
Modelos comparados em src/experimento_modelos.py (um arquivo por modelo).

Todos seguem a interface de src/modelos/base.py: treinar(df, horizonte) e
prever(df, horizonte), que devolve os casos previstos e a tendência.
"""
from src.modelos.baseline_persistencia import BaselinePersistencia
from src.modelos.binomial_negativa import BinomialNegativa
from src.modelos.ensemble import Ensemble
from src.modelos.lightgbm_ajustado import LightGBMAjustado
from src.modelos.lightgbm_atual import LightGBMAtual
from src.modelos.lightgbm_classificador import LightGBMClassificador
from src.modelos.lightgbm_quantis import LightGBMQuantis
from src.modelos.regressao_linear import RegressaoLinear

# Ordem de apresentação nos resultados
MODELOS = [
    BaselinePersistencia,
    RegressaoLinear,
    BinomialNegativa,
    LightGBMAtual,
    LightGBMAjustado,
    LightGBMQuantis,
    LightGBMClassificador,
    Ensemble,
]
