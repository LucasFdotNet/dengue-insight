"""
Experimento: o melhor modelo de tendência contra a sinalização do InfoDengue (Rt).

Pergunta: para dizer se os casos vão subir, ficar estáveis ou cair nas próximas 1 a 4
semanas, o nosso melhor modelo (lightgbm_classificador) é mais útil que o Rt que o
InfoDengue já publica?

O Rt NÃO é usado nos nossos modelos (decisão do projeto: ver README). Aqui ele aparece
só como referência externa de comparação.

Comparados, com a mesma avaliação de experimento_modelos.py (validação cruzada por
município, validação final nos 15 municípios, walk-forward de 2019 em diante):
  - lightgbm_classificador: o melhor modelo da comparação de modelos (resultados lidos de
    reports/comparacao_modelos_por_municipio.csv; rode experimento_modelos.py antes);
  - sinal_rt e sinal_p_rt1: regras diretas com o Rt e o p_rt1 da semana de partida;
  - classificador_rt: LightGBM treinado só com Rt, p_rt1 e casos atuais. Não é candidato a
    modelo do projeto: representa o melhor que se consegue tirar do Rt sozinho, para que a
    comparação não dependa de limiares escolhidos arbitrariamente nas regras.
Detalhes das regras em src/modelos/sinal_rt.py.

Diferenças e intervalos de confiança são sempre em relação ao lightgbm_classificador.

Saídas (mesmo formato de experimento_modelos.py):
  reports/comparacao_rt.csv
  reports/comparacao_rt_por_municipio.csv
"""
import logging

import pandas as pd

from src.experimento_generalizacao import grupos_de_municipios
from src.experimento_modelos import (ARQUIVO_POR_MUNICIPIO, INICIO_COMPARACAO, MESES_POR_RETREINO,
                                     metricas_com_ic, resumo_por_municipio, validacao_cruzada, walk_forward)
from src.modelos.lightgbm_classificador import LightGBMClassificador
from src.modelos.sinal_rt import ClassificadorRt, SinalPRt1, SinalRt
from src.train import carregar

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_METRICAS = 'reports/comparacao_rt.csv'
ARQUIVO_RT_POR_MUNICIPIO = 'reports/comparacao_rt_por_municipio.csv'
REFERENCIA = LightGBMClassificador.nome
MODELOS_RT = [SinalRt, SinalPRt1, ClassificadorRt]


def run_experimento():
    treino, validacao = carregar('treino'), carregar('validacao')
    grupos = grupos_de_municipios(treino['cidade'].unique())
    fim = treino['data_iniSE'].max().to_period('M').strftime('%Y-%m')

    anterior = pd.read_csv(ARQUIVO_POR_MUNICIPIO)
    resumos = [anterior[anterior['modelo'] == REFERENCIA]]
    if resumos[0].empty:
        raise RuntimeError(f"{REFERENCIA} não encontrado em {ARQUIVO_POR_MUNICIPIO}. Rode experimento_modelos.py antes.")

    for classe in MODELOS_RT:
        logging.info(f"Modelo {classe.nome}: validação cruzada por município...")
        cv = validacao_cruzada(classe, treino, grupos, INICIO_COMPARACAO, fim, MESES_POR_RETREINO)
        logging.info(f"Modelo {classe.nome}: validação final...")
        final = walk_forward(classe, treino, validacao, INICIO_COMPARACAO, fim, MESES_POR_RETREINO)
        for conjunto, prev in [('validacao_cruzada', cv), ('validacao_final', final)]:
            resumos.append(resumo_por_municipio(prev).assign(modelo=classe.nome, conjunto=conjunto))

    por_municipio = pd.concat(resumos, ignore_index=True)
    por_municipio.to_csv(ARQUIVO_RT_POR_MUNICIPIO, index=False)

    descricao = {c.nome: c.descricao for c in [LightGBMClassificador] + MODELOS_RT}
    tabelas = []
    for (modelo, conjunto), pm in por_municipio.groupby(['modelo', 'conjunto'], sort=False):
        ref = por_municipio[(por_municipio['modelo'] == REFERENCIA) & (por_municipio['conjunto'] == conjunto)]
        tabelas.append(metricas_com_ic(pm, ref).assign(modelo=modelo, descricao=descricao[modelo], conjunto=conjunto))
    resultado = pd.concat(tabelas, ignore_index=True)
    resultado = resultado[['modelo', 'descricao', 'conjunto', 'h', 'metrica', 'valor', 'ic95_inf', 'ic95_sup',
                           'dif_vs_referencia', 'dif_ic95_inf', 'dif_ic95_sup', 'municipios']]
    resultado.round(4).to_csv(ARQUIVO_METRICAS, index=False)
    logging.info(f"Resultados salvos em {ARQUIVO_METRICAS} e {ARQUIVO_RT_POR_MUNICIPIO}.")
    print(resultado[resultado['metrica'] == 'acerto_balanceado']
          .pivot_table(index=['conjunto', 'modelo'], columns='h', values='valor', sort=False).round(3))


if __name__ == "__main__":
    run_experimento()
