"""
Experimento: comparação de modelos para prever a TENDÊNCIA dos casos.

Pergunta: o LightGBM é o melhor modelo para dizer se, nas próximas 1 a 4 semanas, os
casos vão subir, ficar estáveis ou cair, em municípios que o modelo nunca viu?

Modelos (um arquivo cada, em src/modelos/): baseline de persistência, regressão linear,
binomial negativa, LightGBM atual, LightGBM ajustado, LightGBM por quantis, LightGBM
classificador e ensemble. Todos usam as mesmas informações (casos atuais, variação em
relação a 1-4 semanas atrás e semana do ano), sem clima e sem Rt.

Avaliação (igual para todos):
  - Validação cruzada por município: os 100 municípios de treino em 5 grupos (os mesmos
    de experimento_generalizacao.py); cada grupo é previsto por modelos treinados só com
    os outros 4. É por essa avaliação que os modelos são comparados e escolhidos.
  - Validação final: treino com os 100 municípios e previsão dos 15 de validação.
    Reportada, mas NÃO usada para escolher o modelo.
  - Walk-forward: retreino a cada 3 meses; só entram no treino semanas cujo resultado
    já era conhecido antes do início do período previsto.
  - Período de ajuste: 2015 a 2018, usado só para escolher os hiperparâmetros do
    LightGBM ajustado. Período de comparação: 2019 em diante, para todos os modelos.

Métricas de tendência (principal: acerto balanceado):
  - acerto: fração de semanas com a tendência certa;
  - acerto balanceado: média do acerto em cada classe (sobe, estável, cai). O "sempre
    estável" tem acerto alto só porque a maioria das semanas é estável, mas acerto
    balanceado de 33%; esta métrica não se deixa enganar pela classe mais comum;
  - subidas detectadas, alarmes de subida corretos, quedas detectadas, sentido oposto.
Métricas secundárias: razão entre o erro absoluto do modelo e o do baseline (em casos) e,
para o modelo por quantis, a cobertura do intervalo de 80%.
Intervalos de confiança de 95% por bootstrap sobre municípios (2.000 sorteios); diferenças
para o LightGBM atual com bootstrap pareado.

Saídas (formato "longo", prontas para tabelas e gráficos):
  reports/comparacao_modelos.csv                  métricas com IC 95%, por modelo, conjunto e horizonte
  reports/comparacao_modelos_por_municipio.csv    matriz de confusão e erros por município (base de tudo)
  reports/lightgbm_ajustado_ajuste.csv            resultado da busca em grade
  reports/lightgbm_ajustado_parametros.json       hiperparâmetros escolhidos

Uso:
  python -m src.experimento_modelos                  roda tudo (ajusta o LightGBM se ainda não houver ajuste)
  python -m src.experimento_modelos --reajustar      refaz a busca em grade
  python -m src.experimento_modelos --modelos a,b    roda só os modelos indicados (pelo nome)
"""
import itertools
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

from src.experimento_generalizacao import grupos_de_municipios
from src.modelos import MODELOS
from src.modelos.lightgbm_ajustado import ARQUIVO_PARAMETROS, LightGBMAjustado
from src.avaliacao import (metricas, metricas_com_ic, resumo_por_municipio, validacao_cruzada,  # noqa: F401
                           walk_forward)
from src.train import HORIZONTES, carregar

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_METRICAS = 'reports/comparacao_modelos.csv'
ARQUIVO_POR_MUNICIPIO = 'reports/comparacao_modelos_por_municipio.csv'
ARQUIVO_AJUSTE = 'reports/lightgbm_ajustado_ajuste.csv'

MESES_POR_RETREINO = 3
PERIODO_AJUSTE = ('2015-01', '2018-12')
INICIO_COMPARACAO = '2019-01'
REFERENCIA = 'lightgbm_atual'

GRADE_AJUSTE = {
    'num_leaves': [15, 31, 63],
    'min_child_samples': [20, 100, 400],
    'n_estimators': [150, 400],
}
MESES_POR_RETREINO_AJUSTE = 12


# --------------------------------------------------------------- ajuste do LightGBM

def ajustar_lightgbm(dados, grupos):
    """Busca em grade no período de ajuste; critério: acerto balanceado médio nos 4 horizontes."""
    linhas = []
    combinacoes = [dict(zip(GRADE_AJUSTE, v)) for v in itertools.product(*GRADE_AJUSTE.values())]
    for i, parametros in enumerate(combinacoes, 1):
        parametros = {**parametros, 'learning_rate': 0.05}
        prev = validacao_cruzada(LightGBMAjustado, dados, grupos, *PERIODO_AJUSTE, MESES_POR_RETREINO_AJUSTE,
                                 parametros=parametros)
        pm = resumo_por_municipio(prev)
        por_h = [metricas(pm[pm['h'] == h]) for h in HORIZONTES]
        linha = {**parametros,
                 'acerto_balanceado_medio': np.mean([m['acerto_balanceado'] for m in por_h]),
                 'acerto_medio': np.mean([m['acerto'] for m in por_h]),
                 'razao_mae_media': np.mean([m['razao_mae'] for m in por_h])}
        linhas.append(linha)
        logging.info(f"Ajuste {i}/{len(combinacoes)}: {parametros} -> acerto balanceado "
                     f"{linha['acerto_balanceado_medio']:.4f}")
    tabela = pd.DataFrame(linhas).sort_values('acerto_balanceado_medio', ascending=False)
    tabela.round(4).to_csv(ARQUIVO_AJUSTE, index=False)
    melhor = tabela.iloc[0]
    escolhidos = {k: (int(melhor[k]) if k != 'learning_rate' else float(melhor[k]))
                  for k in list(GRADE_AJUSTE) + ['learning_rate']}
    with open(ARQUIVO_PARAMETROS, 'w', encoding='utf-8') as f:
        json.dump({'parametros': escolhidos,
                   'criterio': 'acerto balanceado médio (H+1 a H+4), validação cruzada por município',
                   'periodo_ajuste': list(PERIODO_AJUSTE)}, f, ensure_ascii=False, indent=2)
    logging.info(f"Hiperparâmetros escolhidos: {escolhidos}")
    return escolhidos


# --------------------------------------------------------------- execução

def run_experimento(nomes=None, reajustar=False):
    treino, validacao = carregar('treino'), carregar('validacao')
    grupos = grupos_de_municipios(treino['cidade'].unique())
    fim = treino['data_iniSE'].max().to_period('M').strftime('%Y-%m')

    if reajustar or not os.path.exists(ARQUIVO_PARAMETROS):
        logging.info("Ajustando os hiperparâmetros do LightGBM...")
        ajustar_lightgbm(treino, grupos)

    classes = [c for c in MODELOS if nomes is None or c.nome in nomes]
    resumos = []
    for classe in classes:
        logging.info(f"Modelo {classe.nome}: validação cruzada por município...")
        cv = validacao_cruzada(classe, treino, grupos, INICIO_COMPARACAO, fim, MESES_POR_RETREINO)
        logging.info(f"Modelo {classe.nome}: validação final...")
        final = walk_forward(classe, treino, validacao, INICIO_COMPARACAO, fim, MESES_POR_RETREINO)
        for conjunto, prev in [('validacao_cruzada', cv), ('validacao_final', final)]:
            resumos.append(resumo_por_municipio(prev).assign(modelo=classe.nome, conjunto=conjunto))

    por_municipio = pd.concat(resumos, ignore_index=True)
    # Mantém os resultados já salvos dos modelos que não foram rodados agora
    if nomes is not None and os.path.exists(ARQUIVO_POR_MUNICIPIO):
        anterior = pd.read_csv(ARQUIVO_POR_MUNICIPIO)
        por_municipio = pd.concat([anterior[~anterior['modelo'].isin(nomes)], por_municipio], ignore_index=True)
    colunas = ['modelo', 'conjunto', 'cidade', 'h'] + [c for c in por_municipio.columns
                                                       if c not in ('modelo', 'conjunto', 'cidade', 'h')]
    por_municipio[colunas].to_csv(ARQUIVO_POR_MUNICIPIO, index=False)

    descricao = {c.nome: c.descricao for c in MODELOS}
    tabelas = []
    for (modelo, conjunto), pm in por_municipio.groupby(['modelo', 'conjunto'], sort=False):
        ref = por_municipio[(por_municipio['modelo'] == REFERENCIA) & (por_municipio['conjunto'] == conjunto)]
        if ref.empty:
            ref = pm
        tabelas.append(metricas_com_ic(pm, ref).assign(modelo=modelo, descricao=descricao.get(modelo, ''),
                                                      conjunto=conjunto))
    resultado = pd.concat(tabelas, ignore_index=True)
    resultado = resultado[['modelo', 'descricao', 'conjunto', 'h', 'metrica', 'valor', 'ic95_inf', 'ic95_sup',
                           'dif_vs_referencia', 'dif_ic95_inf', 'dif_ic95_sup', 'municipios']]
    resultado.round(4).to_csv(ARQUIVO_METRICAS, index=False)
    logging.info(f"Resultados salvos em {ARQUIVO_METRICAS} e {ARQUIVO_POR_MUNICIPIO}.")

    principal = resultado[(resultado['metrica'] == 'acerto_balanceado')]
    print(principal.pivot_table(index=['conjunto', 'modelo'], columns='h', values='valor', sort=False).round(3))


if __name__ == "__main__":
    selecao = None
    if '--modelos' in sys.argv:
        selecao = sys.argv[sys.argv.index('--modelos') + 1].split(',')
    run_experimento(selecao, reajustar='--reajustar' in sys.argv)
