"""
Experimento: outros modelos superam o classificador em produção na tendência?

Compara, com as mesmas informações (casos recentes e clima de S-1 a S-4) e a mesma
avaliação de experimento_modelos.py, o LightGBM classificador com clima (em produção,
referência) com:
  - o mesmo LightGBM com peso igual para as três tendências;
  - o mesmo LightGBM com janela de 12 semanas (a informação que a LSTM recebe);
  - XGBoost (outro boosting de árvores);
  - Random Forest (bagging de árvores);
  - rede neural MLP (mesmas variáveis);
  - rede neural LSTM (sequência das últimas 12 semanas).
Modelos em src/modelos/, um arquivo cada.

Avaliação:
  - validação cruzada por município (5 grupos de 20) e validação final nos 15 municípios
    de validação; walk-forward de 2019 em diante, com retreino a cada 3 meses;
  - redes neurais com SEMENTES_REDES sementes (o resultado varia de uma para outra); as
    métricas somam as previsões das sementes, o que equivale à média de um modelo treinado
    com uma semente qualquer;
  - períodos: desde 2019 (principal, definido antes de rodar) e desde 2022 (pós-pandemia,
    análise de sensibilidade); e métricas por ano, sem intervalo de confiança;
  - além das métricas de tendência, log loss e Brier, que avaliam as probabilidades e não
    dependem do ponto de corte (o peso por classe muda o ponto de corte);
  - intervalos de confiança de 95% por bootstrap sobre municípios e diferença pareada para
    a referência.

Retomada: cada unidade de trabalho (modelo, semente, grupo, trimestre) grava suas
previsões em reports/cache/classificadores/<dados>/, onde <dados> identifica os dados
processados. Se a execução for interrompida, rodar de novo continua de onde parou; se os
dados mudarem, nada antigo é reaproveitado. As unidades rodam em paralelo (PROCESSOS
processos com THREADS núcleos cada).

Saídas:
  reports/comparacao_classificadores.csv                 métricas com IC 95% por modelo, conjunto, período e horizonte
  reports/comparacao_classificadores_por_municipio.csv   matriz de confusão e somas por município (desde 2019)
  reports/comparacao_classificadores_por_ano.csv         métricas por ano
  reports/comparacao_classificadores_sementes.csv        métricas de cada semente (redes neurais)

Uso:
  python -m src.experimento_classificadores                    roda tudo (ou continua)
  python -m src.experimento_classificadores --modelos a,b       só os modelos indicados (pelo nome)
  python -m src.experimento_classificadores --processos 4       muda o número de processos
"""
import functools
import hashlib
import logging
import os
import sys
import time

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits

from src.avaliacao import metricas, metricas_com_ic, resumo_por_municipio
from src.cidades import cidades_por_papel
from src.experimento_generalizacao import grupos_de_municipios
from src.modelos.base import COLUNAS_PROB, tendencia_real
from src.modelos.baseline_persistencia import BaselinePersistencia
from src.modelos.janela import adicionar_janela
from src.modelos.lightgbm_classificador_clima import (ClassificadorClimaBalanceado, ClassificadorClimaJanela12,
                                                      ClassificadorClimaS1S4)
from src.modelos.lstm_classificador import LSTMClassificador
from src.modelos.mlp_classificador import MLPClassificador
from src.modelos.random_forest_classificador import RandomForestClassificador
from src.modelos.xgboost_classificador import XGBoostClassificador
from src.train import HORIZONTES, TENDENCIAS, carregar, linhas_validas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MODELOS = [
    BaselinePersistencia,
    ClassificadorClimaS1S4,
    ClassificadorClimaBalanceado,
    ClassificadorClimaJanela12,
    XGBoostClassificador,
    RandomForestClassificador,
    MLPClassificador,
    LSTMClassificador,
]
REFERENCIA = ClassificadorClimaS1S4.nome
REDES = {MLPClassificador.nome, LSTMClassificador.nome}
SEMENTES_REDES = [42, 43, 44]
SEMENTE_PADRAO = 42

INICIO_COMPARACAO = '2019-01'
PERIODOS = {'desde_2019': '2019-01-01', 'desde_2022': '2022-01-01'}
MESES_POR_RETREINO = 3
PROCESSOS = 8
THREADS = 2

PASTA_CACHE = 'reports/cache/classificadores'
ARQUIVO_METRICAS = 'reports/comparacao_classificadores.csv'
ARQUIVO_POR_MUNICIPIO = 'reports/comparacao_classificadores_por_municipio.csv'
ARQUIVO_POR_ANO = 'reports/comparacao_classificadores_por_ano.csv'
ARQUIVO_SEMENTES = 'reports/comparacao_classificadores_sementes.csv'


# --------------------------------------------------------------- dados

@functools.lru_cache(maxsize=1)
def dados():
    """Treino e validação com a janela de 12 semanas (carregados uma vez por processo)."""
    return adicionar_janela(carregar('treino')), adicionar_janela(carregar('validacao'))


def id_dados():
    """Identifica os dados processados (muda quando os dados são atualizados)."""
    sha = hashlib.sha256()
    for papel in ('treino', 'validacao'):
        for cidade in sorted(cidades_por_papel(papel)):
            with open(os.path.join('data/processed', f'{cidade}_processed.csv'), 'rb') as f:
                sha.update(f.read())
    return sha.hexdigest()[:12]


# --------------------------------------------------------------- unidades de trabalho

def unidades(classes, fim):
    """(modelo, semente, conjunto, início do trimestre) de todas as unidades do experimento."""
    inicios = pd.period_range(INICIO_COMPARACAO, fim, freq='M')[::MESES_POR_RETREINO]
    conjuntos = [f'cv{i}' for i in range(5)] + ['final']
    return [(classe, semente, conjunto, str(inicio))
            for classe in classes
            for semente in (SEMENTES_REDES if classe.nome in REDES else [SEMENTE_PADRAO])
            for conjunto in conjuntos
            for inicio in inicios]


def caminho_unidade(id_, classe, semente, conjunto, inicio):
    return os.path.join(PASTA_CACHE, id_, classe.nome, f's{semente}', f'{conjunto}_{inicio}.parquet')


def executar_unidade(id_, classe, semente, conjunto, inicio):
    """Treina com o que era conhecido no início do trimestre e prevê as semanas do trimestre."""
    destino = caminho_unidade(id_, classe, semente, conjunto, inicio)
    if os.path.exists(destino):
        return destino
    treino, validacao = dados()
    if conjunto == 'final':
        tr_base, te_base = treino, validacao
    else:
        separado = grupos_de_municipios(treino['cidade'].unique())[int(conjunto[2:])]
        tr_base, te_base = treino[~treino['cidade'].isin(separado)], treino[treino['cidade'].isin(separado)]
    ini = pd.Period(inicio, freq='M').start_time
    fim = (pd.Period(inicio, freq='M') + MESES_POR_RETREINO).start_time

    trs, tes = {}, {}
    for h in HORIZONTES:
        tr_h, te_h = linhas_validas(tr_base, h), linhas_validas(te_base, h)
        trs[h] = tr_h[tr_h['data_iniSE'] + pd.Timedelta(weeks=h) < ini]
        tes[h] = te_h[(te_h['data_iniSE'] >= ini) & (te_h['data_iniSE'] < fim)]

    partes = []
    with threadpool_limits(THREADS):
        if getattr(classe, 'multi_horizonte', False):
            unico = classe(semente=semente, threads=THREADS).treinar_horizontes(trs)
            modelos = {h: unico for h in HORIZONTES}
        else:
            modelos = {h: (classe(semente=semente, threads=THREADS) if classe is not BaselinePersistencia
                           else classe()).treinar(trs[h], h) for h in HORIZONTES if not tes[h].empty}
        for h, te in tes.items():
            if te.empty:
                continue
            prev = modelos[h].prever(te, h)
            parte = pd.DataFrame({
                'cidade': te['cidade'].to_numpy(), 'h': h, 'data_iniSE': te['data_iniSE'].to_numpy(),
                'atual': te['casos_est'].to_numpy(), 'real': te[f'target_h{h}'].to_numpy(),
                'tend_real': tendencia_real(te, h), 'tend_prev': prev['tendencia'].to_numpy()})
            for coluna in COLUNAS_PROB.values():
                parte[coluna] = prev[coluna].to_numpy() if coluna in prev else np.nan
            partes.append(parte)

    resultado = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    resultado.to_parquet(destino + '.tmp', index=False, engine='pyarrow')
    os.replace(destino + '.tmp', destino)
    return destino


def rodar_unidades(id_, classes, fim, processos):
    todas = unidades(classes, fim)
    pendentes = [u for u in todas if not os.path.exists(caminho_unidade(id_, *u))]
    logging.info(f"{len(todas)} unidades; {len(todas) - len(pendentes)} já prontas, {len(pendentes)} a rodar "
                 f"({processos} processos x {THREADS} threads).")
    if not pendentes:
        return
    # As unidades mais lentas (redes e Random Forest) primeiro, para equilibrar o fim
    ordem = {c.nome: i for i, c in enumerate(classes)}
    pendentes.sort(key=lambda u: (u[0].nome not in REDES | {RandomForestClassificador.nome}, ordem[u[0].nome]))
    inicio = time.time()
    feitas = 0
    for _ in Parallel(n_jobs=processos, return_as='generator_unordered', batch_size=1)(
            delayed(executar_unidade)(id_, *u) for u in pendentes):
        feitas += 1
        if feitas % 25 == 0 or feitas == len(pendentes):
            decorrido = time.time() - inicio
            restante = decorrido / feitas * (len(pendentes) - feitas)
            logging.info(f"{feitas}/{len(pendentes)} unidades ({decorrido / 60:.0f} min; faltam ~{restante / 60:.0f} min)")


# --------------------------------------------------------------- métricas

def previsoes(id_, classe, semente, fim):
    caminhos = [caminho_unidade(id_, c, s, conj, ini) for c, s, conj, ini in unidades([classe], fim) if s == semente]
    prev = pd.concat([pd.read_parquet(c) for c in caminhos], ignore_index=True)
    # Classificadores não preveem casos (colunas esperadas por resumo_por_municipio)
    return prev.assign(previsto=np.nan, inferior=np.nan, superior=np.nan)


def resumir(id_, classes, fim):
    """Resumo por município (somando as sementes), por ano e por semente."""
    resumos, por_ano, por_semente = [], [], []
    for classe in classes:
        sementes = SEMENTES_REDES if classe.nome in REDES else [SEMENTE_PADRAO]
        for semente in sementes:
            prev = previsoes(id_, classe, semente, fim)
            prev['conjunto'] = np.where(prev['cidade'].isin(list(cidades_por_papel('validacao'))),
                                        'validacao_final', 'validacao_cruzada')
            prev['ano'] = pd.to_datetime(prev['data_iniSE']).dt.year
            for periodo, desde in PERIODOS.items():
                recorte = prev[pd.to_datetime(prev['data_iniSE']) >= desde]
                for conjunto, g in recorte.groupby('conjunto'):
                    pm = resumo_por_municipio(g).assign(modelo=classe.nome, conjunto=conjunto, periodo=periodo,
                                                        semente=semente)
                    resumos.append(pm)
            for (conjunto, ano), g in prev.groupby(['conjunto', 'ano']):
                pm = resumo_por_municipio(g)
                for h in HORIZONTES:
                    por_ano.append({'modelo': classe.nome, 'conjunto': conjunto, 'ano': ano, 'h': h,
                                    'semente': semente, **metricas(pm[pm['h'] == h])})

    pm_sementes = pd.concat(resumos, ignore_index=True)
    for (modelo, conjunto, periodo, semente), g in pm_sementes.groupby(['modelo', 'conjunto', 'periodo', 'semente']):
        if modelo in REDES:
            for h in HORIZONTES:
                por_semente.append({'modelo': modelo, 'conjunto': conjunto, 'periodo': periodo, 'semente': semente,
                                    'h': h, **metricas(g[g['h'] == h])})
    chaves = ['modelo', 'conjunto', 'periodo', 'cidade', 'h']
    por_municipio = pm_sementes.drop(columns='semente').groupby(chaves, sort=False).sum(min_count=1).reset_index()

    # Por ano: média das sementes
    por_ano = pd.DataFrame(por_ano).drop(columns='semente').groupby(['modelo', 'conjunto', 'ano', 'h'],
                                                                    sort=False).mean().reset_index()
    return por_municipio, por_ano, pd.DataFrame(por_semente)


def run_experimento(nomes=None, processos=PROCESSOS):
    treino, _ = dados()
    fim = treino['data_iniSE'].max().to_period('M').strftime('%Y-%m')
    id_ = id_dados()
    classes = [c for c in MODELOS if nomes is None or c.nome in nomes or c.nome == REFERENCIA]
    logging.info(f"Dados {id_} (até {treino['data_iniSE'].max():%d/%m/%Y}); modelos: {[c.nome for c in classes]}")

    rodar_unidades(id_, classes, fim, processos)
    # As métricas usam todos os modelos já calculados para estes dados
    prontos = [c for c in MODELOS
               if all(os.path.exists(caminho_unidade(id_, *u)) for u in unidades([c], fim))]
    por_municipio, por_ano, por_semente = resumir(id_, prontos, fim)

    descricao = {c.nome: c.descricao for c in MODELOS}
    tabelas = []
    for (modelo, conjunto, periodo), pm in por_municipio.groupby(['modelo', 'conjunto', 'periodo'], sort=False):
        ref = por_municipio[(por_municipio['modelo'] == REFERENCIA) & (por_municipio['conjunto'] == conjunto)
                            & (por_municipio['periodo'] == periodo)]
        tabelas.append(metricas_com_ic(pm, ref).assign(modelo=modelo, descricao=descricao[modelo],
                                                      conjunto=conjunto, periodo=periodo))
    resultado = pd.concat(tabelas, ignore_index=True)
    resultado = resultado[['modelo', 'descricao', 'conjunto', 'periodo', 'h', 'metrica', 'valor', 'ic95_inf',
                           'ic95_sup', 'dif_vs_referencia', 'dif_ic95_inf', 'dif_ic95_sup', 'municipios']]
    resultado.round(4).to_csv(ARQUIVO_METRICAS, index=False)
    por_municipio[por_municipio['periodo'] == 'desde_2019'].drop(columns='periodo').to_csv(ARQUIVO_POR_MUNICIPIO,
                                                                                           index=False)
    por_ano.round(4).to_csv(ARQUIVO_POR_ANO, index=False)
    por_semente.round(4).to_csv(ARQUIVO_SEMENTES, index=False)
    logging.info(f"Resultados salvos em {ARQUIVO_METRICAS}, {ARQUIVO_POR_MUNICIPIO}, {ARQUIVO_POR_ANO} "
                 f"e {ARQUIVO_SEMENTES}.")

    pd.set_option('display.width', 200)
    for metrica in ('acerto_balanceado', 'log_loss'):
        tabela = resultado[(resultado['metrica'] == metrica) & (resultado['periodo'] == 'desde_2019')]
        print(f"\n{metrica} (desde 2019)")
        print(tabela.pivot_table(index=['conjunto', 'modelo'], columns='h', values='valor', sort=False).round(3))


if __name__ == "__main__":
    selecao = sys.argv[sys.argv.index('--modelos') + 1].split(',') if '--modelos' in sys.argv else None
    n = int(sys.argv[sys.argv.index('--processos') + 1]) if '--processos' in sys.argv else PROCESSOS
    # Chama pelo nome do módulo, e não por __main__, para os processos paralelos encontrarem as funções
    from src import experimento_classificadores
    experimento_classificadores.run_experimento(selecao, n)
