"""
Random Forest classificador com clima de S-1 a S-4.

Árvores independentes treinadas em amostras diferentes e combinadas por votação
(bagging), em vez de árvores em sequência que corrigem os erros das anteriores
(boosting, LightGBM e XGBoost). Tende a sobreajustar menos, o que poderia ajudar a
generalizar para municípios não vistos. Mesmas variáveis do classificador em produção;
o scikit-learn trata os valores faltantes do clima sem imputação.
"""
from sklearn.ensemble import RandomForestClassifier

from src.modelos.base import Classificador
from src.modelos.lightgbm_classificador_clima import ClassificadorClimaS1S4


class RandomForestClassificador(Classificador):
    nome = 'random_forest_classificador'
    descricao = 'Random Forest classificador com clima de S-1 a S-4'
    features = ClassificadorClimaS1S4.features
    parametros = {'n_estimators': 300, 'min_samples_leaf': 20, 'max_features': 'sqrt'}

    def _novo_modelo(self):
        return RandomForestClassifier(**self.parametros, random_state=self.semente, n_jobs=self.threads)
