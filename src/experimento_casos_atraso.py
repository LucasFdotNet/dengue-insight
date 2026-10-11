"""
Experimento: casos aproximados como o painel os mostra, com 2 semanas de dados atrasados.

O painel parte do último nível confirmado (semana X-2, decisão 17): as duas semanas mais
recentes ainda estão incompletas. A partir dela, mostra os casos aproximados (modelo de
quantis, mediana e faixa de 80%) da semana atual X e das 4 seguintes, ou seja, de 2 a 6
semanas à frente da semana confirmada.

Avaliação como em experimento_niveis.py: walk-forward com retreino trimestral desde 2015,
validação cruzada por município (5 grupos de 20) e validação final nos 15 municípios de
validação. Métricas de 2019 em diante, por antecedência a partir da semana atual:
  - razão de erro: erro absoluto médio do modelo / da persistência (repetir os casos da
    semana confirmada); menor é melhor;
  - cobertura da faixa de 80%: fração das semanas em que o real ficou dentro dela (o ideal
    é perto de 80%);
com IC 95% por bootstrap sobre municípios.

Saídas: reports/casos_atraso.csv; previsões em reports/cache/casos_atraso (usadas por
src/exportar_painel.py na seção Avaliação)

Uso: python -m src.experimento_casos_atraso [--processos N]
"""
import functools
import logging
import os
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits

from src.cidades import cidades_por_papel
from src.experimento_atraso import adicionar_alvos
from src.experimento_generalizacao import grupos_de_municipios
from src.modelos.lightgbm_quantis import LightGBMQuantis
from src.snapshot import id_dados_processados
from src.train import HORIZONTES, PRIMEIRO_ANO_TESTE, carregar, linhas_validas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LACUNAS = [2]
ANTECEDENCIAS = [0, 1, 2, 3, 4]  # a partir da semana atual
HORIZONTES_CASOS = list(range(min(LACUNAS), max(LACUNAS) + max(ANTECEDENCIAS) + 1))  # a partir da confirmada
INICIO_AVALIACAO = '2019-01-01'
MESES_POR_RETREINO = 3
PROCESSOS, THREADS = 8, 2
N_BOOTSTRAP = 2000
SEMENTE = 42
VERSAO_CACHE = 2  # 2: antecedências de 2 a 7 semanas (lacunas 2 e 3)
PASTA_CACHE = 'reports/cache/casos_atraso'
ARQUIVO_SAIDA = 'reports/casos_atraso.csv'


@functools.lru_cache(maxsize=1)
def dados():
    return (adicionar_alvos(carregar('treino'), max(HORIZONTES_CASOS)),
            adicionar_alvos(carregar('validacao'), max(HORIZONTES_CASOS)))


def caminho(id_, conjunto, inicio):
    return os.path.join(PASTA_CACHE, f'{id_}_v{VERSAO_CACHE}', f'{conjunto}_{inicio}.parquet')


def linhas(df, h):
    v = linhas_validas(df, min(h, max(HORIZONTES)))  # o alvo de fato é target_h<H>, filtrado abaixo
    return v[v[f'target_h{h}'].notna()]


def executar_unidade(id_, conjunto, inicio):
    destino = caminho(id_, conjunto, inicio)
    if os.path.exists(destino):
        return
    treino, validacao = dados()
    if conjunto == 'final':
        tr_base, te_base = treino, validacao
    else:
        separado = grupos_de_municipios(treino['cidade'].unique())[int(conjunto[2:])]
        tr_base, te_base = treino[~treino['cidade'].isin(separado)], treino[treino['cidade'].isin(separado)]
    ini = pd.Period(inicio, freq='M').start_time
    fim = (pd.Period(inicio, freq='M') + MESES_POR_RETREINO).start_time
    partes = []
    with threadpool_limits(THREADS):
        for h in HORIZONTES_CASOS:
            tr = linhas(tr_base, h)
            tr = tr[tr['data_iniSE'] + pd.Timedelta(weeks=h) < ini]
            te = linhas(te_base, h)
            te = te[(te['data_iniSE'] >= ini) & (te['data_iniSE'] < fim)]
            if te.empty:
                continue
            p = LightGBMQuantis().treinar(tr, h).prever(te, h)
            partes.append(pd.DataFrame({'cidade': te['cidade'].to_numpy(), 'data_iniSE': te['data_iniSE'].to_numpy(),
                                        'h': h, 'atual': te['casos_est'].to_numpy(),
                                        'real': te[f'target_h{h}'].to_numpy(), 'previsto': p['previsto'].to_numpy(),
                                        'inferior': p['inferior'].to_numpy(), 'superior': p['superior'].to_numpy()}))
    resultado = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    resultado.to_parquet(destino + '.tmp', index=False)
    os.replace(destino + '.tmp', destino)


def previsoes(id_, processos=PROCESSOS, lacuna=2):
    """Previsões de todas as unidades (roda as que faltam); data_alvo e antecedência a partir da semana atual."""
    fim = dados()[0]['data_iniSE'].max().to_period('M').strftime('%Y-%m')
    inicios = [str(p) for p in pd.period_range(f'{PRIMEIRO_ANO_TESTE}-01', fim, freq='M')[::MESES_POR_RETREINO]]
    unidades = [(c, i) for c in [f'cv{k}' for k in range(5)] + ['final'] for i in inicios]
    pendentes = [u for u in unidades if not os.path.exists(caminho(id_, *u))]
    logging.info(f"{len(unidades)} unidades; {len(pendentes)} a rodar.")
    Parallel(n_jobs=processos, batch_size=1)(delayed(executar_unidade)(id_, *u) for u in pendentes)
    p = pd.concat([pd.read_parquet(caminho(id_, *u)) for u in unidades], ignore_index=True)
    p['antecedencia'] = p['h'] - lacuna
    p = p[p['antecedencia'].isin(ANTECEDENCIAS)]
    p['data_alvo'] = p['data_iniSE'] + pd.to_timedelta(7 * p['h'], unit='D')
    p['conjunto'] = np.where(p['cidade'].isin(list(cidades_por_papel('validacao'))), 'validacao_final',
                             'validacao_cruzada')
    return p


def metricas(c):
    return {'razao_erro': c['erro_modelo'] / c['erro_persistencia'], 'cobertura_80': c['dentro'] / c['semanas']}


def run_experimento(processos=PROCESSOS):
    id_ = id_dados_processados()
    rng = np.random.default_rng(SEMENTE)
    linhas_saida = []
    for lacuna in LACUNAS:
        linhas_saida += avaliar(previsoes(id_, processos, lacuna), lacuna, rng)
    r = pd.DataFrame(linhas_saida).round(3)
    r.to_csv(ARQUIVO_SAIDA, index=False)
    print(r.to_string(index=False))


def avaliar(p, lacuna, rng):
    # Semana atual (emissão) = semana confirmada + lacuna; avaliação pela semana de emissão
    p = p[p['data_iniSE'] + pd.Timedelta(weeks=lacuna) >= INICIO_AVALIACAO].copy()
    p['erro_modelo'] = (p['real'] - p['previsto']).abs()
    p['erro_persistencia'] = (p['real'] - p['atual']).abs()
    p['dentro'] = (p['real'] >= p['inferior']) & (p['real'] <= p['superior'])
    linhas_saida = []
    for (conjunto, a), g in p.groupby(['conjunto', 'antecedencia']):
        comp = g.groupby('cidade').agg(erro_modelo=('erro_modelo', 'sum'), erro_persistencia=('erro_persistencia', 'sum'),
                                       dentro=('dentro', 'sum'), semanas=('dentro', 'size'))
        v = comp.to_numpy(float)
        pontual = metricas(dict(zip(comp.columns, v.sum(axis=0))))
        amostras = {k: [] for k in pontual}
        for _ in range(N_BOOTSTRAP):
            m = metricas(dict(zip(comp.columns, v[rng.integers(0, len(v), len(v))].sum(axis=0))))
            for k in pontual:
                amostras[k].append(m[k])
        for k, valor in pontual.items():
            linhas_saida.append({'conjunto': conjunto, 'lacuna': lacuna, 'antecedencia': a, 'metrica': k,
                                 'valor': valor, 'ic95_inf': np.percentile(amostras[k], 2.5),
                                 'ic95_sup': np.percentile(amostras[k], 97.5), 'municipios': len(v),
                                 'semanas': int(comp['semanas'].sum())})
    return linhas_saida


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index('--processos') + 1]) if '--processos' in sys.argv else PROCESSOS
    from src import experimento_casos_atraso
    experimento_casos_atraso.run_experimento(n)
