"""
LightGBM classificador: prevê a tendência (sobe, estável ou cai) diretamente, em vez de
prever o número de casos e depois classificar.

Como o objetivo do projeto passou a ser acertar a tendência, este modelo testa se vale a
pena treinar diretamente para essa pergunta. Ele não produz número de casos, então não
entra nas métricas de erro em casos.
"""
from lightgbm import LGBMClassifier

from src.modelos.base import Classificador
from src.train import FEATURES


class LightGBMClassificador(Classificador):
    nome = 'lightgbm_classificador'
    descricao = 'LightGBM classificador (prevê a tendência diretamente)'
    features = FEATURES
    peso_classes = None
    parametros = {'n_estimators': 300, 'learning_rate': 0.05, 'num_leaves': 31, 'min_child_samples': 20}

    def _novo_modelo(self):
        return LGBMClassifier(**self.parametros, class_weight=self.peso_classes, random_state=self.semente,
                              n_jobs=self.threads, verbose=-1)
