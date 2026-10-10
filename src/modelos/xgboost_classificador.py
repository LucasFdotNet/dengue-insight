"""
XGBoost classificador com clima de S-1 a S-4.

Outro boosting de árvores, com as mesmas variáveis do classificador em produção. Serve
para verificar se o resultado depende da implementação (LightGBM) ou dos dados e das
variáveis. Hiperparâmetros equivalentes aos do LightGBM (300 árvores, taxa 0,05).
"""
import numpy as np
from xgboost import XGBClassifier

from src.modelos.base import Classificador, tendencia_real
from src.modelos.lightgbm_classificador_clima import ClassificadorClimaS1S4


class XGBoostClassificador(Classificador):
    nome = 'xgboost_classificador'
    descricao = 'XGBoost classificador com clima de S-1 a S-4'
    features = ClassificadorClimaS1S4.features
    parametros = {'n_estimators': 300, 'learning_rate': 0.05, 'max_depth': 6}

    def _novo_modelo(self):
        return XGBClassifier(**self.parametros, tree_method='hist', random_state=self.semente,
                             n_jobs=None if self.threads == -1 else self.threads)

    def treinar(self, df, horizonte):
        # O XGBoost exige classes numeradas de 0 a n-1
        y = tendencia_real(df, horizonte)
        self.classes = np.unique(y)
        self.modelo = self._novo_modelo()
        self.modelo.fit(self._x(df), np.searchsorted(self.classes, y))
        return self

    def _classes(self):
        return self.classes
