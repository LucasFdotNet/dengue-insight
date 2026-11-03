"""
Experimento: outros modelos superam o classificador em produção na tendência?

Compara, com as mesmas informações (casos recentes e clima de S-1 a S-4) e a mesma
avaliação de experimento_modelos.py, o LightGBM classificador com clima (em produção,
referência) com:
  - o mesmo LightGBM com hiperparâmetros ajustados;
  - o mesmo LightGBM com peso igual para as três tendências;
  - o mesmo LightGBM com janela de 12 semanas (a informação que a LSTM recebe);
  - XGBoost (outro boosting de árvores);
  - Random Forest (bagging de árvores);
  - rede neural MLP (mesmas variáveis);
  - rede neural LSTM (sequência das últimas 12 semanas).
Modelos em src/modelos/, um arquivo cada.

Etapa 1, ajuste de hiperparâmetros (mesmo orçamento para todos): a configuração padrão de
cada modelo e mais 8 alternativas (GRADES), avaliadas por validação cruzada por município
em 2015-2018, com retreino anual e uma semente. Critério: acerto balanceado médio nos
quatro horizontes (o mesmo do ajuste de experimento_modelos.py). Os 15 municípios de
validação e os anos de 2019 em diante não participam da escolha.

Etapa 2, comparação com a configuração escolhida de cada modelo (o classificador em
produção entra com a configuração padrão, como está no painel):
  - validação cruzada por município (5 grupos de 20) e validação final nos 15 municípios
    de validação; walk-forward de 2019 em diante, com retreino a cada 3 meses;
  - redes neurais com SEMENTES_REDES sementes (o resultado varia de uma para outra); as
    métricas somam as previsões das sementes, o que equivale à média de um modelo treinado
    com uma semente qualquer;
  - períodos: desde 2019 (principal, definido antes de rodar) e desde 2022 (pós-pandemia,
    análise de sensibilidade); e métricas por ano, sem intervalo de confiança;
  - além das métricas de tendência, log loss e Brier, que avaliam as probabilidades e não
    dependem do ponto de corte (o peso por classe muda o ponto de corte);
  - duas regras de decisão para cada classificador sem peso por classe: a tendência mais
    provável (como o modelo foi treinado) e a "decisão balanceada", que divide cada
    probabilidade pela frequência daquela tendência no treino da unidade antes de escolher.
    A decisão balanceada equivale ao peso igual para as três tendências, mas aplicada depois
    do treino, sobre as probabilidades salvas (não exige treinar de novo); detecta mais
    subidas e quedas, com mais alarmes que não se confirmam. Os hiperparâmetros são os
    escolhidos com a regra normal;
  - intervalos de confiança de 95% por bootstrap sobre municípios e diferença pareada para
    a referência.

Retomada: cada unidade de trabalho (modelo, configuração, semente, grupo, período de
retreino) grava suas previsões em reports/cache/classificadores/<dados>/, onde <dados>
identifica os dados processados e cada configuração tem sua pasta. Se a execução for
interrompida, rodar de novo continua de onde parou; se os dados ou a configuração mudarem,
nada antigo é reaproveitado. Mudanças no código de um modelo que não alteram os
hiperparâmetros não são detectadas: nesse caso, apague a pasta do modelo no cache. As
unidades rodam em paralelo (PROCESSOS processos com THREADS núcleos cada).

Saídas:
  reports/ajuste_classificadores.csv                     acerto de cada configuração no ajuste
  reports/ajuste_classificadores_parametros.json         configuração escolhida de cada modelo
  reports/comparacao_classificadores.csv                 métricas com IC 95% por modelo, conjunto, período e horizonte
  reports/comparacao_classificadores_por_municipio.csv   matriz de confusão e somas por município (desde 2019)
  reports/comparacao_classificadores_por_ano.csv         métricas por ano
  reports/comparacao_classificadores_sementes.csv        métricas de cada semente (redes neurais)

Uso:
  python -m src.experimento_classificadores                    roda tudo (ou continua)
  python -m src.experimento_classificadores --processos 4       muda o número de processos
"""
import functools
import hashlib
import itertools
import json
import logging
import os
import sys
import time
from collections import namedtuple

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
from src.snapshot import id_dados_processados
from src.train import HORIZONTES, TENDENCIAS, carregar, linhas_validas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def _grade(**valores):
    """Todas as combinações dos valores (8 com 2 valores para 3 hiperparâmetros)."""
    return [dict(zip(valores, v)) for v in itertools.product(*valores.values())]


GRADE_LIGHTGBM = _grade(num_leaves=[15, 63], min_child_samples=[20, 200], n_estimators=[150, 400])
# Alternativas à configuração padrão de cada classe (o padrão sempre entra; nenhuma alternativa o repete)
GRADES = {
    ClassificadorClimaS1S4: GRADE_LIGHTGBM,
    ClassificadorClimaBalanceado: GRADE_LIGHTGBM,
    ClassificadorClimaJanela12: GRADE_LIGHTGBM,
    XGBoostClassificador: _grade(max_depth=[4, 8], min_child_weight=[1, 10], n_estimators=[150, 400]),
    RandomForestClassificador: _grade(min_samples_leaf=[5, 50], max_features=['sqrt', 0.5], max_depth=[None, 12]),
    MLPClassificador: _grade(hidden_layer_sizes=[(32,), (128, 64)], alpha=[1e-4, 1e-2],
                             learning_rate_init=[1e-3, 3e-3]),
    LSTMClassificador: _grade(oculto=[16, 64], dropout=[0.0, 0.3], taxa=[1e-3, 3e-3]),
}
REFERENCIA = ClassificadorClimaS1S4.nome
REDES = {MLPClassificador.nome, LSTMClassificador.nome}
LENTOS = REDES | {RandomForestClassificador.nome}
SEMENTES_REDES = [42, 43, 44]
SEMENTE_PADRAO = 42

PERIODO_AJUSTE = ('2015-01', '2018-12')
MESES_POR_RETREINO_AJUSTE = 12
INICIO_COMPARACAO = '2019-01'
MESES_POR_RETREINO = 3
PERIODOS = {'desde_2019': '2019-01-01', 'desde_2022': '2022-01-01'}
PROCESSOS = 8
THREADS = 2

PASTA_CACHE = 'reports/cache/classificadores'
# Muda quando o preparo dos dados do experimento muda sem mudar os dados processados (o cache
# antigo deixa de valer). 2: janela.adicionar_janela mantém os var_log_1 a 4 do pré-processamento
VERSAO_CACHE = 2
ARQUIVO_AJUSTE = 'reports/ajuste_classificadores.csv'
ARQUIVO_PARAMETROS = 'reports/ajuste_classificadores_parametros.json'
ARQUIVO_METRICAS = 'reports/comparacao_classificadores.csv'
ARQUIVO_POR_MUNICIPIO = 'reports/comparacao_classificadores_por_municipio.csv'
ARQUIVO_POR_ANO = 'reports/comparacao_classificadores_por_ano.csv'
ARQUIVO_SEMENTES = 'reports/comparacao_classificadores_sementes.csv'

# Um modelo na comparação: nome nas tabelas, classe e hiperparâmetros (alterações ao padrão da classe)
Entrada = namedtuple('Entrada', 'rotulo classe config descricao regra', defaults=['treinada'])
# Uma unidade de trabalho: um treino por trimestre (ou ano, no ajuste) para um grupo de municípios
Unidade = namedtuple('Unidade', 'classe config semente conjunto inicio meses')


# --------------------------------------------------------------- dados

@functools.lru_cache(maxsize=1)
def dados():
    """Treino e validação com a janela de 12 semanas (carregados uma vez por processo)."""
    return adicionar_janela(carregar('treino')), adicionar_janela(carregar('validacao'))


# --------------------------------------------------------------- unidades de trabalho

def parametros_completos(classe, config):
    return classe(parametros=config).parametros if classe is not BaselinePersistencia else {}


def id_config(classe, config):
    """Identifica a configuração completa (hiperparâmetros, peso das classes e variáveis)."""
    exemplo = classe()
    descricao = {'parametros': parametros_completos(classe, config),
                 'peso_classes': getattr(classe, 'peso_classes', None),
                 'features': list(getattr(exemplo, 'features', []))}
    return hashlib.sha256(json.dumps(descricao, sort_keys=True, default=str).encode()).hexdigest()[:10]


def caminho_unidade(id_, u):
    return os.path.join(PASTA_CACHE, f'{id_}_v{VERSAO_CACHE}', u.classe.nome, id_config(u.classe, u.config), f's{u.semente}',
                        f'{u.conjunto}_{u.inicio}_{u.meses}m.parquet')


def executar_unidade(id_, u):
    """Treina com o que era conhecido no início do período e prevê as semanas do período."""
    destino = caminho_unidade(id_, u)
    if os.path.exists(destino):
        return destino
    treino, validacao = dados()
    if u.conjunto == 'final':
        tr_base, te_base = treino, validacao
    else:
        separado = grupos_de_municipios(treino['cidade'].unique())[int(u.conjunto[2:])]
        tr_base, te_base = treino[~treino['cidade'].isin(separado)], treino[treino['cidade'].isin(separado)]
    ini = pd.Period(u.inicio, freq='M').start_time
    fim = (pd.Period(u.inicio, freq='M') + u.meses).start_time

    trs, tes = {}, {}
    for h in HORIZONTES:
        tr_h, te_h = linhas_validas(tr_base, h), linhas_validas(te_base, h)
        trs[h] = tr_h[tr_h['data_iniSE'] + pd.Timedelta(weeks=h) < ini]
        tes[h] = te_h[(te_h['data_iniSE'] >= ini) & (te_h['data_iniSE'] < fim)]

    def novo():
        if u.classe is BaselinePersistencia:
            return u.classe()
        return u.classe(semente=u.semente, threads=THREADS, parametros=u.config)

    partes = []
    with threadpool_limits(THREADS):
        if getattr(u.classe, 'multi_horizonte', False):
            unico = novo().treinar_horizontes(trs)
            modelos = {h: unico for h in HORIZONTES}
        else:
            modelos = {h: novo().treinar(trs[h], h) for h in HORIZONTES if not tes[h].empty}
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


def rodar_unidades(id_, todas, processos, etapa):
    # Grava a configuração ao lado do cache, para consulta
    for u in {(u.classe, json.dumps(u.config, sort_keys=True, default=str)): u for u in todas}.values():
        pasta = os.path.join(PASTA_CACHE, f'{id_}_v{VERSAO_CACHE}', u.classe.nome, id_config(u.classe, u.config))
        os.makedirs(pasta, exist_ok=True)
        with open(os.path.join(pasta, 'config.json'), 'w', encoding='utf-8') as f:
            json.dump(parametros_completos(u.classe, u.config), f, ensure_ascii=False, indent=1, default=str)

    pendentes = [u for u in todas if not os.path.exists(caminho_unidade(id_, u))]
    logging.info(f"{etapa}: {len(todas)} unidades; {len(todas) - len(pendentes)} já prontas, {len(pendentes)} "
                 f"a rodar ({processos} processos x {THREADS} threads).")
    if not pendentes:
        return
    # As unidades mais lentas primeiro, para equilibrar o fim
    pendentes.sort(key=lambda u: u.classe.nome not in LENTOS)
    inicio = time.time()
    feitas = 0
    for _ in Parallel(n_jobs=processos, return_as='generator_unordered', batch_size=1)(
            delayed(executar_unidade)(id_, u) for u in pendentes):
        feitas += 1
        if feitas % 25 == 0 or feitas == len(pendentes):
            decorrido = time.time() - inicio
            restante = decorrido / feitas * (len(pendentes) - feitas)
            logging.info(f"{etapa}: {feitas}/{len(pendentes)} unidades ({decorrido / 60:.0f} min; "
                         f"faltam ~{restante / 60:.0f} min)")


@functools.lru_cache(maxsize=None)
def frequencias_treino(conjunto, inicio, h):
    """Frequência de cada tendência (ordem de TENDENCIAS) nas linhas de treino de uma unidade."""
    treino, _ = dados()
    if conjunto != 'final':
        treino = treino[~treino['cidade'].isin(grupos_de_municipios(treino['cidade'].unique())[int(conjunto[2:])])]
    v = linhas_validas(treino, h)
    v = v[v['data_iniSE'] + pd.Timedelta(weeks=h) < pd.Period(inicio, freq='M').start_time]
    frequencia = pd.Series(tendencia_real(v, h)).value_counts(normalize=True)
    return np.array([frequencia.get(t, 0.0) for t in TENDENCIAS])


def decisao_balanceada(prev, u):
    """Tendência com maior probabilidade dividida pela frequência no treino da unidade."""
    prev = prev.copy()
    colunas = [COLUNAS_PROB[t] for t in TENDENCIAS]
    for h, g in prev.groupby('h'):
        relativa = g[colunas].to_numpy() / np.maximum(frequencias_treino(u.conjunto, u.inicio, h), 1e-9)
        prev.loc[g.index, 'tend_prev'] = np.array(TENDENCIAS)[relativa.argmax(axis=1)]
    return prev


def ler_previsoes(id_, unidades_, regra='treinada'):
    partes = []
    for u in unidades_:
        prev = pd.read_parquet(caminho_unidade(id_, u))
        partes.append(decisao_balanceada(prev, u) if regra == 'balanceada' and not prev.empty else prev)
    prev = pd.concat(partes, ignore_index=True)
    # Classificadores não preveem casos (colunas esperadas por resumo_por_municipio)
    return prev.assign(previsto=np.nan, inferior=np.nan, superior=np.nan)


# --------------------------------------------------------------- etapa 1: ajuste

def unidades_ajuste(classe, config):
    inicios = pd.period_range(*PERIODO_AJUSTE, freq='M')[::MESES_POR_RETREINO_AJUSTE]
    return [Unidade(classe, config, SEMENTE_PADRAO, f'cv{i}', str(ini), MESES_POR_RETREINO_AJUSTE)
            for i in range(5) for ini in inicios]


def ajustar(id_, processos):
    candidatos = [(classe, config) for classe, grade in GRADES.items() for config in [{}] + grade]
    rodar_unidades(id_, [u for c in candidatos for u in unidades_ajuste(*c)], processos, 'Ajuste')

    linhas = []
    for classe, config in candidatos:
        pm = resumo_por_municipio(ler_previsoes(id_, unidades_ajuste(classe, config)))
        por_h = {h: metricas(pm[pm['h'] == h]) for h in HORIZONTES}
        pm_bal = resumo_por_municipio(ler_previsoes(id_, unidades_ajuste(classe, config), 'balanceada'))
        linhas.append({'modelo': classe.nome, 'config': json.dumps(config, default=str), 'padrao': not config,
                       **{f'acerto_balanceado_h{h}': m['acerto_balanceado'] for h, m in por_h.items()},
                       'acerto_balanceado_medio': np.mean([m['acerto_balanceado'] for m in por_h.values()]),
                       'log_loss_medio': np.mean([m['log_loss'] for m in por_h.values()]),
                       'acerto_balanceado_medio_decisao_balanceada':
                           np.mean([metricas(pm_bal[pm_bal['h'] == h])['acerto_balanceado'] for h in HORIZONTES])})
    tabela = pd.DataFrame(linhas)
    tabela.round(4).to_csv(ARQUIVO_AJUSTE, index=False)

    escolhidos = {}
    for modelo, g in tabela.groupby('modelo', sort=False):
        melhor = g.sort_values('acerto_balanceado_medio', ascending=False).iloc[0]
        escolhidos[modelo] = json.loads(melhor['config'])
        logging.info(f"Ajuste de {modelo}: {melhor['config']} (acerto balanceado médio "
                     f"{melhor['acerto_balanceado_medio']:.4f}; padrão "
                     f"{g[g['padrao']]['acerto_balanceado_medio'].iloc[0]:.4f})")
    with open(ARQUIVO_PARAMETROS, 'w', encoding='utf-8') as f:
        json.dump({'id_dados': id_, 'periodo_ajuste': list(PERIODO_AJUSTE),
                   'criterio': 'acerto balanceado médio (H+1 a H+4), validação cruzada por município',
                   'modelos': escolhidos}, f, ensure_ascii=False, indent=2)
    return escolhidos


# --------------------------------------------------------------- etapa 2: comparação

def entradas_comparacao(escolhidos):
    def config(classe):
        # JSON transforma tuplas em listas; o MLP precisa de tupla nas camadas
        c = dict(escolhidos[classe.nome])
        if 'hidden_layer_sizes' in c:
            c['hidden_layer_sizes'] = tuple(c['hidden_layer_sizes'])
        return c

    entradas = [Entrada(BaselinePersistencia.nome, BaselinePersistencia, {}, BaselinePersistencia.descricao),
                Entrada(REFERENCIA, ClassificadorClimaS1S4, {},
                        ClassificadorClimaS1S4.descricao + ' (em produção, configuração padrão)')]
    for classe in GRADES:
        rotulo = classe.nome + ('_ajustado' if classe is ClassificadorClimaS1S4 else '')
        entradas.append(Entrada(rotulo, classe, config(classe), classe.descricao + ' (hiperparâmetros ajustados)'))
    # Decisão balanceada para os classificadores treinados sem peso por classe
    for e in [e for e in entradas if e.classe in GRADES and getattr(e.classe, 'peso_classes', None) is None]:
        entradas.append(e._replace(rotulo=e.rotulo + '_decisao_balanceada', regra='balanceada',
                                   descricao=e.descricao.rstrip(')') + '; decisão balanceada)'))
    return entradas


def unidades_comparacao(entrada, fim):
    inicios = pd.period_range(INICIO_COMPARACAO, fim, freq='M')[::MESES_POR_RETREINO]
    sementes = SEMENTES_REDES if entrada.classe.nome in REDES else [SEMENTE_PADRAO]
    return [Unidade(entrada.classe, entrada.config, s, conjunto, str(ini), MESES_POR_RETREINO)
            for s in sementes for conjunto in [f'cv{i}' for i in range(5)] + ['final'] for ini in inicios]


def resumir(id_, entradas, fim):
    """Resumo por município (somando as sementes), por ano e por semente."""
    validacao = list(cidades_por_papel('validacao'))
    resumos, por_ano, por_semente = [], [], []
    for e in entradas:
        unidades_ = unidades_comparacao(e, fim)
        for semente in sorted({u.semente for u in unidades_}):
            prev = ler_previsoes(id_, [u for u in unidades_ if u.semente == semente], e.regra)
            prev['conjunto'] = np.where(prev['cidade'].isin(validacao), 'validacao_final', 'validacao_cruzada')
            prev['data_iniSE'] = pd.to_datetime(prev['data_iniSE'])
            for periodo, desde in PERIODOS.items():
                for conjunto, g in prev[prev['data_iniSE'] >= desde].groupby('conjunto'):
                    pm = resumo_por_municipio(g).assign(modelo=e.rotulo, conjunto=conjunto, periodo=periodo)
                    resumos.append(pm)
                    if e.classe.nome in REDES:
                        for h in HORIZONTES:
                            por_semente.append({'modelo': e.rotulo, 'conjunto': conjunto, 'periodo': periodo,
                                                'semente': semente, 'h': h, **metricas(pm[pm['h'] == h])})
            for (conjunto, ano), g in prev.groupby(['conjunto', prev['data_iniSE'].dt.year.rename('ano')]):
                pm = resumo_por_municipio(g)
                for h in HORIZONTES:
                    por_ano.append({'modelo': e.rotulo, 'conjunto': conjunto, 'ano': ano, 'h': h,
                                    **metricas(pm[pm['h'] == h])})

    chaves = ['modelo', 'conjunto', 'periodo', 'cidade', 'h']
    por_municipio = pd.concat(resumos, ignore_index=True).groupby(chaves, sort=False).sum(min_count=1).reset_index()
    por_ano = pd.DataFrame(por_ano).groupby(['modelo', 'conjunto', 'ano', 'h'], sort=False).mean().reset_index()
    return por_municipio, por_ano, pd.DataFrame(por_semente)


def comparar(id_, escolhidos, processos):
    treino, _ = dados()
    fim = treino['data_iniSE'].max().to_period('M').strftime('%Y-%m')
    entradas = entradas_comparacao(escolhidos)
    # As entradas com decisão balanceada usam as mesmas unidades das entradas com a regra normal
    rodar_unidades(id_, [u for e in entradas if e.regra == 'treinada' for u in unidades_comparacao(e, fim)],
                   processos, 'Comparação')
    por_municipio, por_ano, por_semente = resumir(id_, entradas, fim)

    descricao = {e.rotulo: e.descricao for e in entradas}
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


def run_experimento(processos=PROCESSOS):
    id_ = id_dados_processados()
    logging.info(f"Dados {id_}.")
    escolhidos = ajustar(id_, processos)
    comparar(id_, escolhidos, processos)


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index('--processos') + 1]) if '--processos' in sys.argv else PROCESSOS
    # Chama pelo nome do módulo, e não por __main__, para os processos paralelos encontrarem as funções
    from src import experimento_classificadores
    experimento_classificadores.run_experimento(n)
