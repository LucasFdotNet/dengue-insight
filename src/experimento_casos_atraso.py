"""
Experimento: casos aproximados como o painel os mostra, com 2 semanas de dados atrasados.

O painel parte do último nível confirmado (semana X-2, decisão 17): as duas semanas mais
recentes ainda estão incompletas. A partir dela, mostra os casos aproximados (mediana e faixa de
80%) da semana atual X e das 4 seguintes, ou seja, de 2 a 6 semanas à frente da semana confirmada.

Modelo: o do painel desde a decisão 18, o de quantis com o clima, que dá também a chance de cada
nível (experimento_niveis_quantis.py); os casos são os quantis de 50% (mediana), 10% e 90% das
mesmas previsões fora da amostra (walk-forward com retreino trimestral desde 2015, validação
cruzada por município em 5 grupos de 20 e validação final nos 15 municípios de validação).
Métricas de 2019 em diante, por antecedência a partir da semana atual:
  - razão de erro: erro absoluto médio do modelo / da persistência (repetir os casos da
    semana confirmada); menor é melhor;
  - cobertura da faixa de 80%: fração das semanas em que o real ficou dentro dela (o ideal
    é perto de 80%);
com IC 95% por bootstrap sobre municípios.

Saída: reports/casos_atraso.csv

Uso: python -m src.experimento_casos_atraso [--processos N]
"""
import logging
import sys

import numpy as np
import pandas as pd

from src import experimento_niveis_quantis as enq
from src.cidades import cidades_por_papel
from src.snapshot import id_dados_processados

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LACUNAS = [2]
ANTECEDENCIAS = [0, 1, 2, 3, 4]  # a partir da semana atual
INICIO_AVALIACAO = '2019-01-01'
PROCESSOS = enq.PROCESSOS
N_BOOTSTRAP = 2000
SEMENTE = 42
ARQUIVO_SAIDA = 'reports/casos_atraso.csv'


def previsoes(id_, processos=PROCESSOS, lacuna=2):
    """Casos previstos fora da amostra (mediana e faixa de 80%), com os casos da semana confirmada
    ('atual') e os reais; data_alvo e antecedência a partir da semana atual."""
    p = enq.previsoes_producao(id_, processos)
    p = p.rename(columns={'q50': 'previsto', 'q10': 'inferior', 'q90': 'superior'})
    treino, validacao = enq.dados()
    base = pd.concat([treino, validacao], ignore_index=True)
    reais = base.melt(id_vars=['cidade', 'data_iniSE', 'casos_est'],
                      value_vars=[f'target_h{h}' for h in sorted(p['h'].unique())], var_name='h', value_name='real')
    reais['h'] = reais['h'].str.split('_h').str[1].astype(int)
    p = p.merge(reais.rename(columns={'casos_est': 'atual'}), on=['cidade', 'data_iniSE', 'h'], how='left')
    p['antecedencia'] = p['h'] - lacuna
    p = p[p['antecedencia'].isin(ANTECEDENCIAS) & p['real'].notna()]
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
