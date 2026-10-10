"""
Números do relatório final que não saem prontos de outro script.

Antes eram cálculos avulsos que só imprimiam na tela; aqui gravam em reports/relatorio/,
para o relatório citar arquivos e o pipeline (pipeline_completo.py) refazê-los com os
dados novos.

Saídas (reports/relatorio/):
  base_dados.csv                    tamanho da base: municípios, semanas, primeira e última semana
  casos_por_ano_foco.csv            casos estimados, notificados, pico semanal e incidência por ano
                                    nos municípios em foco (Tabela 1)
  correlacao_clima_mediana.csv      correlação entre log dos casos e o clima k semanas antes
                                    (mediana dos 100 municípios de treino, k = 0 a 16)
  correlacao_clima_defasagem.csv    defasagem de maior correlação em cada município (resumo)
  correlacao_clima_foco.csv         correlações dos municípios em foco
  metricas_producao.csv             métricas de tendência e cobertura do intervalo do painel
                                    (walk-forward desde 2015), por grupo e horizonte
  metricas_producao_foco.csv        idem, nos municípios em foco (todos os anos e só 2024)
  tabela_acerto_balanceado.csv      acerto balanceado "valor [IC 95%]" de todos os modelos
                                    comparados (experimentos de modelos, Rt, clima e classificadores)

Uso:
  python -m src.numeros_relatorio
"""
import logging
import os

import numpy as np
import pandas as pd

from src.cidades import CIDADES, cidades_por_papel
from src.train import ARQUIVO_PREVISOES_PASSADAS, TENDENCIAS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PASTA = 'reports/relatorio'
FOCO = ['campinas', 'cosmopolis', 'piracicaba']
VARIAVEIS_CLIMA = ['tmed', 'precipitacao', 'umidade']
DEFASAGENS = range(0, 17, 2)
COMPARACOES = ['reports/comparacao_modelos.csv', 'reports/comparacao_rt.csv',
               'reports/comparacao_clima_classificador.csv', 'reports/comparacao_classificadores.csv']


def processado(cidade):
    return pd.read_csv(f'data/processed/{cidade}_processed.csv', parse_dates=['data_iniSE']).sort_values('data_iniSE')


def salvar(df, nome, **kwargs):
    caminho = os.path.join(PASTA, nome)
    df.to_csv(caminho, **kwargs)
    logging.info(f"Salvo: {caminho}")


# --------------------------------------------------------------- base de dados

def base_e_casos():
    datas = {c: processado(c)['data_iniSE'] for c in CIDADES}
    salvar(pd.DataFrame([{'municipios': len(CIDADES), 'semanas': sum(len(d) for d in datas.values()),
                          'primeira_semana': min(d.min() for d in datas.values()).date(),
                          'ultima_semana': max(d.max() for d in datas.values()).date()}]),
           'base_dados.csv', index=False)

    linhas = []
    for cidade in FOCO:
        df = processado(cidade)
        pop = df['pop'].iloc[-1]
        por_ano = df.groupby(df['data_iniSE'].dt.year.rename('ano')).agg(
            casos_est=('casos_est', 'sum'), casos_notificados=('casos', 'sum'), pico_semanal=('casos_est', 'max'))
        por_ano['incidencia_100mil'] = (por_ano['casos_est'] / pop * 1e5).round(0)
        linhas.append(por_ano.reset_index().assign(cidade=cidade, populacao=pop))
    salvar(pd.concat(linhas)[['cidade', 'populacao', 'ano', 'casos_est', 'casos_notificados', 'pico_semanal',
                              'incidencia_100mil']], 'casos_por_ano_foco.csv', index=False)


# --------------------------------------------------------------- correlação defasada com o clima

def correlacao_clima():
    linhas = []
    for cidade in cidades_por_papel('treino'):
        df = processado(cidade)
        y = np.log1p(df['casos_est'])
        for variavel in VARIAVEIS_CLIMA:
            for k in DEFASAGENS:
                linhas.append({'cidade': cidade, 'variavel': variavel, 'defasagem_semanas': k,
                               'correlacao': y.corr(df[variavel].shift(k))})
    r = pd.DataFrame(linhas)
    salvar(r.groupby(['variavel', 'defasagem_semanas'])['correlacao'].median().unstack().round(3),
           'correlacao_clima_mediana.csv')
    melhor = r.loc[r.groupby(['cidade', 'variavel'])['correlacao'].idxmax()]
    salvar(melhor.groupby('variavel')['defasagem_semanas'].describe().round(2), 'correlacao_clima_defasagem.csv')
    salvar(r[r['cidade'].isin(FOCO)].pivot_table(index=['cidade', 'variavel'], columns='defasagem_semanas',
                                                  values='correlacao').round(2), 'correlacao_clima_foco.csv')


# --------------------------------------------------------------- métricas do modelo em produção

def metricas_semanas(g):
    real, prev = g['tend_real'], g['tend_prev']
    detectadas = {t: ((real == t) & (prev == t)).sum() / max((real == t).sum(), 1) for t in TENDENCIAS}
    return pd.Series({
        'semanas': len(g),
        'acerto': (real == prev).mean(),
        'acerto_balanceado': np.mean(list(detectadas.values())),
        'subidas_detectadas': detectadas['sobe'],
        'alarmes_subida_corretos': ((prev == 'sobe') & (real == 'sobe')).sum() / max((prev == 'sobe').sum(), 1),
        'sentido_oposto': (((prev == 'sobe') & (real == 'cai')) | ((prev == 'cai') & (real == 'sobe'))).mean(),
        'cobertura_intervalo_80': ((g['real'] >= g['inferior']) & (g['real'] <= g['superior'])).mean(),
    })


def metricas_producao():
    df = pd.read_csv(ARQUIVO_PREVISOES_PASSADAS)
    papel = {**{c: 'treino' for c in cidades_por_papel('treino')}, **{c: 'validacao' for c in cidades_por_papel('validacao')}}
    df['grupo'] = df['cidade'].map(papel)
    salvar(df.groupby(['grupo', 'h']).apply(metricas_semanas).round(3), 'metricas_producao.csv')
    foco = df[df['cidade'].isin(FOCO)]
    todos = foco.groupby(['cidade', 'h']).apply(metricas_semanas).assign(periodo='todos os anos')
    ano_2024 = foco[foco['data_alvo'].str.startswith('2024')].groupby(['cidade', 'h']).apply(metricas_semanas)
    salvar(pd.concat([todos, ano_2024.assign(periodo='2024')]).round(3), 'metricas_producao_foco.csv')


# --------------------------------------------------------------- tabela de comparação de modelos

def tabela_comparacao():
    partes = []
    for arquivo in COMPARACOES:
        if not os.path.exists(arquivo):
            logging.warning(f"{arquivo} não encontrado; fica fora da tabela de comparação.")
            continue
        d = pd.read_csv(arquivo).assign(fonte=os.path.basename(arquivo))
        if 'periodo' in d:
            d = d[d['periodo'] == 'desde_2019']
        partes.append(d)
    d = pd.concat(partes).drop_duplicates(['modelo', 'conjunto', 'h', 'metrica'])
    d = d[d['metrica'] == 'acerto_balanceado']
    d['valor_ic'] = d.apply(lambda x: f"{x['valor']:.3f} [{x['ic95_inf']:.3f}–{x['ic95_sup']:.3f}]", axis=1)
    salvar(d.pivot_table(index=['conjunto', 'fonte', 'modelo'], columns='h', values='valor_ic', aggfunc='first'),
           'tabela_acerto_balanceado.csv')


def run_numeros():
    os.makedirs(PASTA, exist_ok=True)
    base_e_casos()
    correlacao_clima()
    metricas_producao()
    tabela_comparacao()


if __name__ == "__main__":
    run_numeros()
