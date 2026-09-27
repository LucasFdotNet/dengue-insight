"""
Experimento: o clima ajuda o LightGBM classificador (melhor modelo de tendência)?

O teste de clima de experimento_generalizacao.py foi feito com o LightGBM de regressão:
lá, o clima piorou a previsão de 1 semana, não fez diferença em 2 e 3 semanas e melhorou
um pouco a de 4 semanas (S-1 a S-4 e S-1 a S-5). Este experimento repete o teste com o
classificador, que foi o melhor na comparação de modelos (experimento_modelos.py).

Comparados (mesma avaliação de experimento_modelos.py: validação cruzada por município,
validação final nos 15 municípios, walk-forward de 2019 em diante, retreino a cada 3 meses):
  - lightgbm_classificador (sem clima): resultados lidos de
    reports/comparacao_modelos_por_municipio.csv (rode experimento_modelos.py antes);
  - lightgbm_classificador_clima_s1_s4 e lightgbm_classificador_clima_s1_s5
    (src/modelos/lightgbm_classificador_clima.py).
Diferenças e intervalos de confiança em relação ao classificador sem clima.

Saídas (mesmo formato de experimento_modelos.py):
  reports/comparacao_clima_classificador.csv
  reports/comparacao_clima_classificador_por_municipio.csv
"""
import logging

import pandas as pd

from src.experimento_clima_semanal import adicionar_clima
from src.experimento_generalizacao import grupos_de_municipios
from src.experimento_modelos import (ARQUIVO_POR_MUNICIPIO, INICIO_COMPARACAO, MESES_POR_RETREINO,
                                     metricas_com_ic, resumo_por_municipio, validacao_cruzada, walk_forward)
from src.modelos.lightgbm_classificador import LightGBMClassificador
from src.modelos.lightgbm_classificador_clima import ClassificadorClimaS1S4, ClassificadorClimaS1S5
from src.train import carregar

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_METRICAS = 'reports/comparacao_clima_classificador.csv'
ARQUIVO_CLIMA_POR_MUNICIPIO = 'reports/comparacao_clima_classificador_por_municipio.csv'
REFERENCIA = LightGBMClassificador.nome
MODELOS_CLIMA = [ClassificadorClimaS1S4, ClassificadorClimaS1S5]


def run_experimento():
    treino, validacao = adicionar_clima(carregar('treino')), adicionar_clima(carregar('validacao'))
    grupos = grupos_de_municipios(treino['cidade'].unique())
    fim = treino['data_iniSE'].max().to_period('M').strftime('%Y-%m')

    anterior = pd.read_csv(ARQUIVO_POR_MUNICIPIO)
    resumos = [anterior[anterior['modelo'] == REFERENCIA]]
    if resumos[0].empty:
        raise RuntimeError(f"{REFERENCIA} não encontrado em {ARQUIVO_POR_MUNICIPIO}. Rode experimento_modelos.py antes.")

    for classe in MODELOS_CLIMA:
        logging.info(f"Modelo {classe.nome}: validação cruzada por município...")
        cv = validacao_cruzada(classe, treino, grupos, INICIO_COMPARACAO, fim, MESES_POR_RETREINO)
        logging.info(f"Modelo {classe.nome}: validação final...")
        final = walk_forward(classe, treino, validacao, INICIO_COMPARACAO, fim, MESES_POR_RETREINO)
        for conjunto, prev in [('validacao_cruzada', cv), ('validacao_final', final)]:
            resumos.append(resumo_por_municipio(prev).assign(modelo=classe.nome, conjunto=conjunto))

    por_municipio = pd.concat(resumos, ignore_index=True)
    por_municipio.to_csv(ARQUIVO_CLIMA_POR_MUNICIPIO, index=False)

    descricao = {c.nome: c.descricao for c in [LightGBMClassificador] + MODELOS_CLIMA}
    tabelas = []
    for (modelo, conjunto), pm in por_municipio.groupby(['modelo', 'conjunto'], sort=False):
        ref = por_municipio[(por_municipio['modelo'] == REFERENCIA) & (por_municipio['conjunto'] == conjunto)]
        tabelas.append(metricas_com_ic(pm, ref).assign(modelo=modelo, descricao=descricao[modelo], conjunto=conjunto))
    resultado = pd.concat(tabelas, ignore_index=True)
    resultado = resultado[['modelo', 'descricao', 'conjunto', 'h', 'metrica', 'valor', 'ic95_inf', 'ic95_sup',
                           'dif_vs_referencia', 'dif_ic95_inf', 'dif_ic95_sup', 'municipios']]
    resultado.round(4).to_csv(ARQUIVO_METRICAS, index=False)
    logging.info(f"Resultados salvos em {ARQUIVO_METRICAS} e {ARQUIVO_CLIMA_POR_MUNICIPIO}.")
    print(resultado[resultado['metrica'] == 'acerto_balanceado']
          .pivot_table(index=['conjunto', 'modelo'], columns='h', values='valor', sort=False).round(3))


if __name__ == "__main__":
    run_experimento()
