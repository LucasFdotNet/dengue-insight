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
from src.modelos.base import tendencia_real
from src.modelos.lightgbm_ajustado import ARQUIVO_PARAMETROS, LightGBMAjustado
from src.train import HORIZONTES, TENDENCIAS, carregar, linhas_validas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_METRICAS = 'reports/comparacao_modelos.csv'
ARQUIVO_POR_MUNICIPIO = 'reports/comparacao_modelos_por_municipio.csv'
ARQUIVO_AJUSTE = 'reports/lightgbm_ajustado_ajuste.csv'

MESES_POR_RETREINO = 3
PERIODO_AJUSTE = ('2015-01', '2018-12')
INICIO_COMPARACAO = '2019-01'
REFERENCIA = 'lightgbm_atual'
N_BOOTSTRAP = 2000
SEMENTE = 42

GRADE_AJUSTE = {
    'num_leaves': [15, 31, 63],
    'min_child_samples': [20, 100, 400],
    'n_estimators': [150, 400],
}
MESES_POR_RETREINO_AJUSTE = 12


# --------------------------------------------------------------- avaliação walk-forward

def walk_forward(classe, treino, teste, inicio, fim, meses_por_retreino, **kwargs):
    """Previsões de 'teste' por modelos treinados com 'treino', retreinados periodicamente."""
    meses = pd.period_range(inicio, fim, freq='M')[::meses_por_retreino]
    partes = []
    for h in HORIZONTES:
        passo = pd.Timedelta(weeks=h)
        tr_h, te_h = linhas_validas(treino, h), linhas_validas(teste, h)
        for mes in meses:
            ini, fim_mes = mes.start_time, (mes + meses_por_retreino).start_time
            tr = tr_h[tr_h['data_iniSE'] + passo < ini]
            te = te_h[(te_h['data_iniSE'] >= ini) & (te_h['data_iniSE'] < min(fim_mes, pd.Period(fim).end_time))]
            if te.empty:
                continue
            modelo = classe(**kwargs).treinar(tr, h)
            prev = modelo.prever(te, h)
            partes.append(pd.DataFrame({
                'cidade': te['cidade'].values,
                'h': h,
                'data_iniSE': te['data_iniSE'].values,
                'atual': te['casos_est'].values,
                'real': te[f'target_h{h}'].values,
                'previsto': prev['previsto'].values,
                'inferior': prev['inferior'].values if 'inferior' in prev else np.nan,
                'superior': prev['superior'].values if 'superior' in prev else np.nan,
                'tend_real': tendencia_real(te, h),
                'tend_prev': prev['tendencia'].values,
            }))
    return pd.concat(partes, ignore_index=True)


def validacao_cruzada(classe, dados, grupos, inicio, fim, meses_por_retreino, **kwargs):
    partes = []
    for separado in grupos:
        partes.append(walk_forward(classe, dados[~dados['cidade'].isin(separado)],
                                   dados[dados['cidade'].isin(separado)], inicio, fim,
                                   meses_por_retreino, **kwargs))
    return pd.concat(partes, ignore_index=True)


# --------------------------------------------------------------- métricas

def resumo_por_municipio(prev):
    """Matriz de confusão e somas de erro por município e horizonte (base de todas as métricas)."""
    linhas = []
    for (cidade, h), g in prev.groupby(['cidade', 'h']):
        linha = {'cidade': cidade, 'h': h, 'semanas': len(g),
                 'erro_abs_modelo': (g['real'] - g['previsto']).abs().sum() if g['previsto'].notna().all() else np.nan,
                 'erro_abs_baseline': (g['real'] - g['atual']).abs().sum(),
                 'dentro_intervalo': ((g['real'] >= g['inferior']) & (g['real'] <= g['superior'])).sum()
                 if g['inferior'].notna().all() else np.nan}
        for r in TENDENCIAS:
            for p in TENDENCIAS:
                linha[f'real_{r}_prev_{p}'] = int(((g['tend_real'] == r) & (g['tend_prev'] == p)).sum())
        linhas.append(linha)
    return pd.DataFrame(linhas)


COLUNAS_SOMA = ['semanas', 'erro_abs_modelo', 'erro_abs_baseline', 'dentro_intervalo'] +     [f'real_{r}_prev_{p}' for r in TENDENCIAS for p in TENDENCIAS]


def metricas_de_somas(soma):
    """Métricas a partir das somas das colunas de resumo_por_municipio (dict coluna -> soma)."""
    c = {(r, p): soma[f'real_{r}_prev_{p}'] for r in TENDENCIAS for p in TENDENCIAS}
    total = sum(c.values())
    real = {r: sum(c[(r, p)] for p in TENDENCIAS) for r in TENDENCIAS}
    prev = {p: sum(c[(r, p)] for r in TENDENCIAS) for p in TENDENCIAS}
    recall = [c[(r, r)] / real[r] for r in TENDENCIAS if real[r]]
    return {
        'acerto': sum(c[(t, t)] for t in TENDENCIAS) / total,
        'acerto_balanceado': float(np.mean(recall)),
        'subidas_detectadas': c[('sobe', 'sobe')] / real['sobe'] if real['sobe'] else np.nan,
        'alarmes_subida_corretos': c[('sobe', 'sobe')] / prev['sobe'] if prev['sobe'] else np.nan,
        'quedas_detectadas': c[('cai', 'cai')] / real['cai'] if real['cai'] else np.nan,
        'sentido_oposto': (c[('sobe', 'cai')] + c[('cai', 'sobe')]) / total,
        # NaN quando o modelo não prevê casos (classificador) ou não tem intervalo
        'razao_mae': soma['erro_abs_modelo'] / soma['erro_abs_baseline'],
        'cobertura_intervalo_80': soma['dentro_intervalo'] / soma['semanas'],
    }


def metricas(pm):
    """Métricas de um conjunto de municípios (qualquer subconjunto de resumo_por_municipio)."""
    return metricas_de_somas(pm[COLUNAS_SOMA].sum(skipna=False).to_dict())


def metricas_com_ic(pm_modelo, pm_referencia):
    """Métricas por horizonte com IC 95% (bootstrap sobre municípios) e diferença pareada para a referência."""
    rng = np.random.default_rng(SEMENTE)
    linhas = []
    for h in HORIZONTES:
        a = pm_modelo[pm_modelo['h'] == h].set_index('cidade').sort_index()
        b = pm_referencia[pm_referencia['h'] == h].set_index('cidade').reindex(a.index)
        va, vb = a[COLUNAS_SOMA].to_numpy(float), b[COLUNAS_SOMA].to_numpy(float)
        pontual, pontual_ref = metricas(a), metricas(b)
        amostras = {k: [] for k in pontual}
        difs = {k: [] for k in pontual}
        for _ in range(N_BOOTSTRAP):
            idx = rng.integers(0, len(a), len(a))
            ma = metricas_de_somas(dict(zip(COLUNAS_SOMA, va[idx].sum(axis=0))))
            mb = metricas_de_somas(dict(zip(COLUNAS_SOMA, vb[idx].sum(axis=0))))
            for k in pontual:
                amostras[k].append(ma[k])
                difs[k].append(ma[k] - mb[k])
        for k, v in pontual.items():
            if np.isnan(v):
                continue
            tem_ref = not np.isnan(pontual_ref[k])
            linhas.append({
                'h': h, 'metrica': k, 'valor': v,
                'ic95_inf': np.nanpercentile(amostras[k], 2.5), 'ic95_sup': np.nanpercentile(amostras[k], 97.5),
                'dif_vs_referencia': v - pontual_ref[k] if tem_ref else np.nan,
                'dif_ic95_inf': np.nanpercentile(difs[k], 2.5) if tem_ref else np.nan,
                'dif_ic95_sup': np.nanpercentile(difs[k], 97.5) if tem_ref else np.nan,
                'municipios': len(a),
            })
    return pd.DataFrame(linhas)


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
