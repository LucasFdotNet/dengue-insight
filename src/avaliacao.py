"""
Avaliação comum a train.py e aos experimentos: walk-forward genérico (para qualquer
modelo de src/modelos/), validação cruzada por município e métricas de tendência e de
erro em casos, com intervalos de confiança por bootstrap sobre municípios.
"""
import numpy as np
import pandas as pd

from src.modelos.base import tendencia_real
from src.train import HORIZONTES, TENDENCIAS, linhas_validas

N_BOOTSTRAP = 2000
SEMENTE = 42


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
