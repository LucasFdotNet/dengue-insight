"""
LightGBM com hiperparâmetros ajustados.

Os hiperparâmetros são escolhidos por experimento_modelos.py (função ajustar_lightgbm),
numa busca em grade avaliada pela validação cruzada por município no período de ajuste
(2015 a 2018), que não se sobrepõe ao período de comparação (2019 em diante). A escolha
fica salva em ARQUIVO_PARAMETROS e é lida aqui.
"""
import json
import os

from src.modelos.lightgbm_atual import LightGBMAtual

ARQUIVO_PARAMETROS = 'reports/lightgbm_ajustado_parametros.json'


class LightGBMAjustado(LightGBMAtual):
    nome = 'lightgbm_ajustado'
    descricao = 'LightGBM com hiperparâmetros ajustados (busca em grade, 2015-2018)'

    def __init__(self, parametros=None):
        if parametros is None:
            if not os.path.exists(ARQUIVO_PARAMETROS):
                raise FileNotFoundError(f"{ARQUIVO_PARAMETROS} não encontrado. Rode experimento_modelos.py "
                                        "para fazer o ajuste.")
            with open(ARQUIVO_PARAMETROS, encoding='utf-8') as f:
                parametros = json.load(f)['parametros']
        self.parametros = parametros
