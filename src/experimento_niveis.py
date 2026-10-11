"""
Experimento: previsão de três níveis (verde, amarelo, vermelho) e comparação de definições.

Definições (src/estados.VARIANTES_NIVEIS), com limiares por município calculados só com os
anos anteriores:
  A: amarelo a partir do percentil 75, vermelho a partir do 90;
  B: amarelo do percentil 80 ao 97 (faixa em torno do 90), vermelho a partir do 97;
  C: canal endêmico do Ministério da Saúde: amarelo acima da mediana e vermelho acima do Q3 dos
     casos da mesma semana epidemiológica nos 5 anos anteriores;
  D: MEM, como o InfoDengue (src/mem.py): amarelo a partir do limiar pré-epidêmico e vermelho a
     partir do limiar epidêmico, recalculados a cada temporada com as temporadas anteriores.

Previsões: como em experimento_estados.py (walk-forward com retreino trimestral desde 2015,
validação cruzada por município e validação final), com o modelo de src/modelos/nivel_lightgbm.py.

Antecedências: 2, 3 e 4 semanas (HORIZONTES_NIVEIS). A previsão de 1 semana ficou de fora: é quase
uma cópia do nível atual (ganho de menos de 1 ponto sobre a persistência) e dá pouco tempo para
mobilizar.

Nível previsto para S+H: o mais provável. (Testada e descartada: escolher vermelho quando a
probabilidade de vermelho passa de um corte em que, no passado, pelo menos metade das previsões
de vermelho se confirmou; semana a semana, prevê vermelho demais e perde para a persistência.)
Alerta de mobilização: entrada no vermelho (maior probabilidade de vermelho em S+2 a S+4), com o
corte calibrado por alarme, como em experimento_estados.py. Comparação: persistência (o nível de S se mantém em S+H).

Métricas por semana (2019 em diante): acerto, acerto balanceado, acerto nas semanas em que o
nível muda entre S e S+H, vermelho detectado, previsões de vermelho corretas, epidemias
perdidas (previu verde, veio vermelho) e alarmes graves (previu vermelho, veio verde).
Métricas por episódio do vermelho (mobilização): como em experimento_estados.py. Alertas por
antecedência: semanas, a partir de uma semana não vermelha, em que a probabilidade de vermelho em
S+H passou do corte do alerta, e o nível que de fato veio em S+H.

Saídas:
  reports/niveis_semanas.csv, reports/niveis_episodios.csv, reports/niveis_cortes.csv,
  reports/niveis_alertas_antecedencia.csv
  reports/figures/niveis/quadradinhos_<município>_<definição>.png, com a definição pelo nome
  (mem, percentis_80_97, canal_endemico); com --resumo, também a comparação das definições A e B
  reports/figures/niveis/casos_<município>.png: casos, limiares do MEM e a previsão do modelo de
  quantis (src/train.py, reports/previsoes_walkforward.csv) no mesmo período dos quadradinhos

Uso:
  python -m src.experimento_niveis              previsões, métricas e quadradinhos
  python -m src.experimento_niveis --resumo     também os gráficos de comparação de A e B
"""
import functools
import logging
import os
import sys

import matplotlib
import matplotlib.dates
import matplotlib.ticker
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402
from threadpoolctl import threadpool_limits  # noqa: E402

from src import experimento_estados as ee  # noqa: E402
from src.cidades import CIDADES, cidades_por_papel  # noqa: E402
from src.estados import DESCRICAO_VARIANTES, VARIANTES_NIVEIS, adicionar_niveis  # noqa: E402
from src.experimento_generalizacao import grupos_de_municipios  # noqa: E402
from src.modelos.nivel_lightgbm import NivelLightGBM  # noqa: E402
from src.snapshot import id_dados_processados  # noqa: E402
from src.train import (ARQUIVO_PREVISOES_PASSADAS, HORIZONTES, PRIMEIRO_ANO_TESTE, carregar,  # noqa: E402
                       linhas_validas)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INICIO_AVALIACAO = ee.INICIO_AVALIACAO
MESES_POR_RETREINO = 3
PRECISAO_MINIMA = 0.5
CORTES = ee.CORTES
PROCESSOS, THREADS = 8, 2
VERSAO_CACHE = 1
PASTA_CACHE = 'reports/cache/niveis'
PASTA_FIGURAS = 'reports/figures/niveis'
ARQUIVO_SEMANAS = 'reports/niveis_semanas.csv'
ARQUIVO_EPISODIOS = 'reports/niveis_episodios.csv'
ARQUIVO_CORTES = 'reports/niveis_cortes.csv'
ARQUIVO_ALERTAS_H = 'reports/niveis_alertas_antecedencia.csv'
# Sem a previsão de 1 semana: quase uma cópia do nível atual, com pouco tempo para mobilizar (decisão 16)
HORIZONTES_NIVEIS = [h for h in HORIZONTES if h >= 2]
# Alvos até 8 semanas: o teste de atraso (experimento_niveis_robustez.py) prevê antecedência + lacuna
HORIZONTE_MAXIMO = 8
# Exemplos para os quadradinhos: um município de treino e um de validação, com epidemias recentes
EXEMPLOS = [(c, '2023-07-01', '2025-07-01') for c in ('campinas', 'sorocaba', 'fortaleza', 'blumenau')]
VARIANTES_QUADRADINHOS = ['B', 'C', 'D']
# Nome da definição no arquivo dos quadradinhos (a letra é só o nome interno)
ARQUIVO_VARIANTE = {'A': 'percentis_75_90', 'B': 'percentis_80_97', 'C': 'canal_endemico', 'D': 'mem'}

# Cores (paleta de status do guia de visualização; sempre com legenda em texto)
COR_NIVEL = {0: '#0ca30c', 1: '#fab219', 2: '#d03b3b'}
COR_VARIANTE = {'A': '#2a78d6', 'B': '#eb6834'}
TINTA, TINTA_SEC, MUDO, GRADE, FUNDO = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#fcfcfb'


# --------------------------------------------------------------- previsões

@functools.lru_cache(maxsize=2)
def dados(variante):
    return (adicionar_niveis(carregar('treino'), variante, HORIZONTE_MAXIMO),
            adicionar_niveis(carregar('validacao'), variante, HORIZONTE_MAXIMO))


def caminho(id_, variante, conjunto, inicio):
    return os.path.join(PASTA_CACHE, f'{id_}_v{VERSAO_CACHE}', variante, f'{conjunto}_{inicio}.parquet')


def executar_unidade(id_, variante, conjunto, inicio, horizontes=None, destino=None):
    horizontes = horizontes or HORIZONTES_NIVEIS
    destino = destino or caminho(id_, variante, conjunto, inicio)
    if os.path.exists(destino):
        return
    treino, validacao = dados(variante)
    if conjunto == 'final':
        tr_base, te_base = treino, validacao
    else:
        separado = grupos_de_municipios(treino['cidade'].unique())[int(conjunto[2:])]
        tr_base, te_base = treino[~treino['cidade'].isin(separado)], treino[treino['cidade'].isin(separado)]
    ini = pd.Period(inicio, freq='M').start_time
    fim = (pd.Period(inicio, freq='M') + MESES_POR_RETREINO).start_time
    partes = []
    with threadpool_limits(THREADS):
        for h in horizontes:
            tr = linhas_validas(tr_base, min(h, max(HORIZONTES)))  # o alvo de fato é faixa_h<H>, filtrado abaixo
            tr = tr[tr[f'faixa_h{h}'].notna() & (tr['data_iniSE'] + pd.Timedelta(weeks=h) < ini)]
            te = linhas_validas(te_base, min(h, max(HORIZONTES)))
            te = te[te[f'faixa_h{h}'].notna() & (te['data_iniSE'] >= ini) & (te['data_iniSE'] < fim)]
            if te.empty:
                continue
            p = NivelLightGBM(threads=THREADS).treinar(tr, h).prever(te, h)
            partes.append(pd.DataFrame({'cidade': te['cidade'].to_numpy(), 'data_iniSE': te['data_iniSE'].to_numpy(),
                                        'h': h, 'p0': p[:, 0], 'p1': p[:, 1], 'p2': p[:, 2]}))
    resultado = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    resultado.to_parquet(destino + '.tmp', index=False)
    os.replace(destino + '.tmp', destino)


def rodar_previsoes(id_, fim, processos):
    inicios = [str(p) for p in pd.period_range(f'{PRIMEIRO_ANO_TESTE}-01', fim, freq='M')[::MESES_POR_RETREINO]]
    unidades = [(v, c, i) for v in VARIANTES_NIVEIS for c in [f'cv{k}' for k in range(5)] + ['final'] for i in inicios]
    pendentes = [u for u in unidades if not os.path.exists(caminho(id_, *u))]
    logging.info(f"{len(unidades)} unidades; {len(pendentes)} a rodar.")
    Parallel(n_jobs=processos, batch_size=1)(delayed(executar_unidade)(id_, *u) for u in pendentes)
    return unidades


def tabela_longa(id_, variante, unidades):
    """Uma linha por município, semana S e antecedência: probabilidades, faixa em S e faixa real em S+H (nivel_futuro)."""
    prev = pd.concat([pd.read_parquet(caminho(id_, *u)) for u in unidades if u[0] == variante], ignore_index=True)
    prev = prev[prev['h'].isin(HORIZONTES_NIVEIS)]  # unidades antigas do cache também têm a de 1 semana
    treino, validacao = dados(variante)
    base = pd.concat([treino, validacao], ignore_index=True)
    futuro = base.melt(id_vars=['cidade', 'data_iniSE', 'faixa'], value_vars=[f'faixa_h{h}' for h in HORIZONTES_NIVEIS],
                       var_name='h', value_name='nivel_futuro')
    futuro['h'] = futuro['h'].str[-1].astype(int)
    t = prev.merge(futuro, on=['cidade', 'data_iniSE', 'h'], how='left')
    t['conjunto'] = np.where(t['cidade'].isin(list(cidades_por_papel('validacao'))), 'validacao_final',
                             'validacao_cruzada')
    return t


# --------------------------------------------------------------- nível previsto

def escolher_cortes(t):
    """Cortes de amarelo e vermelho por antecedência e trimestre, só com o passado (validação cruzada)."""
    linhas = []
    cv = t[(t['conjunto'] == 'validacao_cruzada') & t['nivel_futuro'].notna()]
    for h in HORIZONTES_NIVEIS:
        g = cv[cv['h'] == h]
        for trimestre in pd.period_range(INICIO_AVALIACAO[:7], t['data_iniSE'].max(), freq='Q'):
            passado = g[g['data_iniSE'] + pd.Timedelta(weeks=h) < trimestre.start_time]
            cortes = {}
            for nome, prob, real in [('vermelho', passado['p2'], passado['nivel_futuro'] == 2),
                                     ('amarelo', passado['p1'] + passado['p2'], passado['nivel_futuro'] >= 1)]:
                prob, real = prob.to_numpy(), real.to_numpy()
                cortes[nome] = next((c for c in CORTES if (prob >= c).sum() >= 20
                                     and real[prob >= c].mean() >= PRECISAO_MINIMA), np.nan)
            linhas.append({'h': h, 'trimestre': str(trimestre), 'corte_amarelo': cortes['amarelo'],
                           'corte_vermelho': cortes['vermelho']})
    return pd.DataFrame(linhas)


def prever_nivel(t, cortes):
    """nivel_previsto: o nível mais provável (regra adotada). nivel_corte: regra dos cortes (testada e descartada:
    com pelo menos metade das previsões de vermelho confirmadas, prevê vermelho demais semana a semana e perde
    para a persistência; os cortes servem para o alerta de mobilização, que parte do nível normal)."""
    t['nivel_previsto'] = t[['p0', 'p1', 'p2']].to_numpy().argmax(axis=1)
    tri = t['data_iniSE'].dt.to_period('Q').astype(str)
    c = cortes.set_index(['h', 'trimestre'])
    chave = pd.MultiIndex.from_arrays([t['h'], tri])
    ca, cv = c['corte_amarelo'].reindex(chave).to_numpy(), c['corte_vermelho'].reindex(chave).to_numpy()
    t['nivel_corte'] = np.where(t['p2'] >= cv, 2, np.where(t['p1'] + t['p2'] >= ca, 1, 0))
    t.loc[np.isnan(cv) & np.isnan(ca), 'nivel_corte'] = np.nan
    return t


def metricas_semana(real, prev, atual):
    real, prev, atual = (np.asarray(x, dtype=float) for x in (real, prev, atual))
    acertos = [(prev[real == k] == k).mean() for k in range(3) if (real == k).any()]
    muda = real != atual
    return {'semanas': len(real), 'acerto': (prev == real).mean(), 'acerto_balanceado': np.mean(acertos),
            'acerto_quando_muda': (prev[muda] == real[muda]).mean() if muda.any() else np.nan,
            'vermelho_detectado': (prev[real == 2] == 2).mean() if (real == 2).any() else np.nan,
            'vermelho_correto': (real[prev == 2] == 2).mean() if (prev == 2).any() else np.nan,
            'epidemias_perdidas': (prev[real == 2] == 0).mean() if (real == 2).any() else np.nan,
            'alarmes_graves': (real[prev == 2] == 0).mean() if (prev == 2).any() else np.nan}


# --------------------------------------------------------------- mobilização no vermelho (por episódio)

def episodios_vermelho(t, variante):
    """Avaliação por episódio do vermelho, com as funções de experimento_estados (alto = vermelho)."""
    treino, validacao = dados(variante)
    base = pd.concat([treino, validacao], ignore_index=True)
    p_max = t.pivot_table(index=['cidade', 'data_iniSE'], columns='h', values='p2').max(axis=1).rename('p_max')
    s = base[['cidade', 'data_iniSE', 'faixa', 'razao_vermelho', 'var_log_1', 'var_log_2']]
    s = s.merge(p_max.reset_index(), on=['cidade', 'data_iniSE'], how='left').sort_values(['cidade', 'data_iniSE'])
    s['alto'] = (s['faixa'] == 2).where(s['faixa'].notna())
    s['conjunto'] = np.where(s['cidade'].isin(list(cidades_por_papel('validacao'))), 'validacao_final',
                             'validacao_cruzada')
    futuro = pd.concat([s.groupby('cidade')['alto'].shift(-k) for k in range(1, 5)], axis=1)
    s['entra_4sem'] = futuro.max(axis=1, skipna=False)
    s['regra'] = (s['var_log_1'] > 0) & (s['var_log_2'] > s['var_log_1']) & (s['razao_vermelho'] >= np.log(0.5))
    s['infodengue'] = False  # a comparação com o InfoDengue está em experimento_estados.py
    s = s.reset_index(drop=True)
    cortes = ee.escolher_cortes(s)
    s = ee.aplicar_cortes(s, cortes)
    linhas = []
    for conjunto, g in s.groupby('conjunto'):
        for sinal, nome in [('modelo_alerta', 'Modelo: alerta de vermelho'), ('regra', 'Regra simples')]:
            linhas.append({'variante': variante, 'conjunto': conjunto, 'metodo': nome, **ee.avaliar(g, sinal)})
    return linhas, s


def alertas_por_antecedencia(t, alertas):
    """Previsões que acenderam o alerta: em S não vermelho, probabilidade de vermelho em S+H acima do corte."""
    s = alertas[['cidade', 'data_iniSE', 'alto', 'corte_alerta']]
    a = t.merge(s, on=['cidade', 'data_iniSE'], how='left')
    a['alerta_h'] = (a['alto'] == False) & (a['p2'] >= a['corte_alerta'])  # noqa: E712
    return a


def resumo_alertas_por_antecedencia(a, variante):
    linhas = []
    x = a[a['alerta_h'] & (a['data_iniSE'] >= INICIO_AVALIACAO) & a['nivel_futuro'].notna()]
    for (conjunto, h), g in x.groupby(['conjunto', 'h']):
        linhas.append({'variante': variante, 'conjunto': conjunto, 'h': h, 'semanas_com_alerta': len(g),
                       'veio_vermelho': (g['nivel_futuro'] == 2).mean(),
                       'veio_amarelo': (g['nivel_futuro'] == 1).mean(),
                       'veio_verde': (g['nivel_futuro'] == 0).mean()})
    return linhas


# --------------------------------------------------------------- gráficos

def estilo(ax):
    ax.set_facecolor(FUNDO)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    for lado in ('left', 'bottom'):
        ax.spines[lado].set_color('#c3c2b7')
    ax.tick_params(colors=MUDO, labelsize=9)
    ax.grid(axis='y', color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def grafico_comparacao(semanas):
    """Pequenos múltiplos: modelo e persistência das duas definições, por antecedência."""
    s = semanas[semanas['conjunto'] == 'validacao_cruzada']
    paineis = [('acerto', 'Acerto (todas as semanas)'),
               ('acerto_quando_muda', 'Acerto quando o nível muda (persistência: 0%)'),
               ('vermelho_detectado', 'Semanas vermelhas previstas como vermelho'),
               ('vermelho_correto', 'Previsões de vermelho que se confirmaram')]
    fig, eixos = plt.subplots(2, 2, figsize=(11, 7.5), facecolor=FUNDO)
    for ax, (metrica, titulo) in zip(eixos.flat, paineis):
        estilo(ax)
        for v in VARIANTES_NIVEIS:
            for metodo, estilo_linha in [('modelo', '-'), ('persistencia', '--')]:
                x = s[(s['variante'] == v) & (s['metodo'] == metodo)].sort_values('h')
                ax.plot(x['h'], 100 * x[metrica], estilo_linha, color=COR_VARIANTE[v], linewidth=2,
                        marker='o', markersize=6, markeredgecolor=FUNDO, markeredgewidth=1.5,
                        label=f"{v}: {'modelo' if metodo == 'modelo' else 'persistência'}")
        ax.set_title(titulo, loc='left', fontsize=11, color=TINTA)
        ax.set_xticks(HORIZONTES_NIVEIS, [f'{h} sem.' for h in HORIZONTES_NIVEIS])
        ax.set_ylim(0, 100)
        ax.yaxis.set_major_formatter(lambda v, _: f'{v:.0f}%')
    eixos[0, 0].legend(frameon=False, fontsize=9, labelcolor=TINTA_SEC, loc='lower left', handlelength=3.5)
    fig.suptitle('Três níveis: definição A (amarelo ≥ p75, vermelho ≥ p90) × B (amarelo ≥ p80, vermelho ≥ p97)\n'
                 'Nível mais provável × persistência; validação cruzada por município, 2019 em diante',
                 x=0.06, ha='left', fontsize=12, color=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    caminho_fig = os.path.join(PASTA_FIGURAS, 'comparacao_definicoes.png')
    fig.savefig(caminho_fig, dpi=150, facecolor=FUNDO)
    plt.close(fig)
    return caminho_fig


def grafico_alertas(episodios_):
    """Alerta de mobilização (entrada no vermelho) nas duas definições, contra a regra simples."""
    e = episodios_[episodios_['conjunto'] == 'validacao_cruzada']
    paineis = [('epidemias_avisadas', 'Epidemias avisadas antes de começar', True),
               ('alarmes_corretos', 'Alarmes que se confirmaram', True),
               ('alarmes_falsos_por_municipio_ano', 'Alarmes falsos por município por ano', False)]
    fig, eixos = plt.subplots(1, 3, figsize=(12, 4), facecolor=FUNDO)
    metodos = [('Modelo: alerta de vermelho', 'modelo'), ('Regra simples', 'regra simples')]
    for ax, (metrica, titulo, pct) in zip(eixos, paineis):
        estilo(ax)
        for i, v in enumerate(VARIANTES_NIVEIS):
            for j, (metodo, rotulo) in enumerate(metodos):
                valor = e[(e['variante'] == v) & (e['metodo'] == metodo)][metrica].iloc[0]
                valor = 100 * valor if pct else valor
                x = i * 3 + j
                ax.bar(x, valor, width=0.8, color=COR_VARIANTE[v], alpha=1.0 if j == 0 else 0.45,
                       edgecolor=FUNDO, linewidth=2)
                ax.text(x, valor, f'{valor:.0f}%' if pct else f'{valor:.2f}', ha='center', va='bottom',
                        fontsize=9, color=TINTA)
        ax.set_xticks([0, 1, 3, 4], ['A: modelo', 'A: regra', 'B: modelo', 'B: regra'], fontsize=9)
        ax.set_title(titulo, loc='left', fontsize=11, color=TINTA)
        if pct:
            ax.set_ylim(0, 100)
            ax.yaxis.set_major_formatter(lambda v, _: f'{v:.0f}%')
    fig.suptitle('Alerta de mobilização (entrada no vermelho): definição A (vermelho ≥ p90) × B (vermelho ≥ p97)\n'
                 'Validação cruzada por município, episódios de 2019 em diante; aviso até 4 semanas antes do início',
                 x=0.06, ha='left', fontsize=12, color=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    caminho_fig = os.path.join(PASTA_FIGURAS, 'alertas_definicoes.png')
    fig.savefig(caminho_fig, dpi=150, facecolor=FUNDO)
    plt.close(fig)
    return caminho_fig


def grafico_quadradinhos(t, variante, cidade, inicio, fim):
    """O que aconteceu e, para cada antecedência, o nível mais provável (acertos e erros se veem pela cor)."""
    alvo = t[(t['cidade'] == cidade)].copy()
    alvo['data_alvo'] = alvo['data_iniSE'] + pd.to_timedelta(7 * alvo['h'], unit='D')
    alvo = alvo[(alvo['data_alvo'] >= inicio) & (alvo['data_alvo'] < fim)]
    treino, validacao = dados(variante)
    base = pd.concat([treino, validacao])
    real = base[(base['cidade'] == cidade) & (base['data_iniSE'] >= inicio) & (base['data_iniSE'] < fim)]
    semanas = sorted(real['data_iniSE'])
    pos = {d: i for i, d in enumerate(semanas)}
    fig, ax = plt.subplots(figsize=(14, 4.3), facecolor=FUNDO)
    ax.set_facecolor(FUNDO)
    linhas = ['Aconteceu'] + [f'Previsto {h} sem. antes' for h in HORIZONTES_NIVEIS]
    linha_y = {h: (i + 1) * 1.15 + 0.25 for i, h in enumerate(HORIZONTES_NIVEIS)}
    for _, r in real.iterrows():
        if pd.notna(r['faixa']):
            ax.add_patch(plt.Rectangle((pos[r['data_iniSE']], 0), 0.86, 0.86,
                                       facecolor=COR_NIVEL[int(r['faixa'])], linewidth=0))
    for _, r in alvo.iterrows():
        if pd.isna(r['nivel_previsto']) or r['data_alvo'] not in pos:
            continue
        y, x = linha_y[r['h']], pos[r['data_alvo']]
        ax.add_patch(plt.Rectangle((x, y), 0.86, 0.86, facecolor=COR_NIVEL[int(r['nivel_previsto'])], linewidth=0))
    ax.set_xlim(-0.5, len(semanas) + 0.5)
    ax.set_ylim(-0.3, len(HORIZONTES_NIVEIS) * 1.15 + 1.3)
    ax.invert_yaxis()
    ax.set_yticks([0.43] + [linha_y[h] + 0.43 for h in HORIZONTES_NIVEIS], linhas)
    meses = [(i, d) for i, d in enumerate(semanas) if d.day <= 7 and d.month in (1, 4, 7, 10)]
    ax.set_xticks([i for i, _ in meses], [d.strftime('%m/%Y') for _, d in meses])
    ax.tick_params(colors=TINTA_SEC, labelsize=9, length=0)
    for lado in ax.spines.values():
        lado.set_visible(False)
    nome = CIDADES[cidade]['nome']
    papel = 'validação' if cidade in cidades_por_papel('validacao') else 'treino'
    ax.set_title(f'{nome} ({papel}) · definição {variante} ({DESCRICAO_VARIANTES[variante]})\n'
                 'Cada coluna é uma semana. Nas linhas "Previsto x sem. antes", o quadrado mostra o nível mais provável '
                 'previsto x semanas antes para aquela semana;\na previsão acertou quando a cor é a mesma da linha '
                 '"Aconteceu" na mesma coluna.',
                 loc='left', fontsize=10, color=TINTA)
    legenda = [plt.Rectangle((0, 0), 1, 1, color=COR_NIVEL[k]) for k in range(3)]
    rotulos = ['verde: normal', 'amarelo: elevado', 'vermelho: epidêmico']
    ax.legend(legenda, rotulos, ncol=3, frameon=False, fontsize=9, labelcolor=TINTA_SEC,
              loc='upper left', bbox_to_anchor=(0, -0.12))
    fig.tight_layout()
    caminho_fig = os.path.join(PASTA_FIGURAS, f'quadradinhos_{cidade}_{ARQUIVO_VARIANTE[variante]}.png')
    fig.savefig(caminho_fig, dpi=150, facecolor=FUNDO)
    plt.close(fig)
    return caminho_fig


def grafico_casos(cidade, inicio, fim):
    """Casos, limiares do MEM e a previsão do modelo de quantis 2 a 4 semanas antes, alinhados aos quadradinhos."""
    treino, validacao = dados('D')
    base = pd.concat([treino, validacao])
    real = base[(base['cidade'] == cidade) & (base['data_iniSE'] >= inicio) & (base['data_iniSE'] < fim)]
    prev = pd.read_csv(ARQUIVO_PREVISOES_PASSADAS, parse_dates=['data_alvo'])
    prev = prev[(prev['cidade'] == cidade) & (prev['data_alvo'] >= inicio) & (prev['data_alvo'] < fim)]
    linhas = [None] + HORIZONTES_NIVEIS
    fig, eixos = plt.subplots(len(linhas), 1, figsize=(14, 8.5), sharex=True, sharey=True, facecolor=FUNDO)
    for ax, h in zip(eixos, linhas):
        estilo(ax)
        ax.step(real['data_iniSE'], real['limiar_vermelho'], where='post', color=COR_NIVEL[2], linewidth=1.2,
                linestyle='--')
        ax.step(real['data_iniSE'], real['limiar_amarelo'], where='post', color=COR_NIVEL[1], linewidth=1.2,
                linestyle='--')
        if h is None:
            ax.plot(real['data_iniSE'], real['casos_est'], color=TINTA, linewidth=2)
            ax.set_title('Aconteceu', loc='left', fontsize=10, color=TINTA)
            continue
        p = prev[prev['h'] == h].sort_values('data_alvo')
        ax.fill_between(p['data_alvo'], p['inferior'], p['superior'], color=COR_VARIANTE['A'], alpha=0.18,
                        linewidth=0)
        ax.plot(real['data_iniSE'], real['casos_est'], color=MUDO, linewidth=1.2)
        ax.plot(p['data_alvo'], p['previsto'], color=COR_VARIANTE['A'], linewidth=2)
        ax.set_title(f'Previsto {h} sem. antes', loc='left', fontsize=10, color=TINTA)
    # Escala logarítmica: os limiares e as fases de poucos casos ficam visíveis ao lado dos picos
    topo = max(real['casos_est'].max(), prev[prev['h'].isin(HORIZONTES_NIVEIS)]['superior'].max())
    eixos[0].set_yscale('log', nonpositive='clip')
    eixos[0].set_ylim(1, topo * 1.5)
    eixos[0].yaxis.set_major_formatter(lambda v, _: f'{v:,.0f}'.replace(',', '.'))
    eixos[0].yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    eixos[-1].set_xlim(pd.Timestamp(inicio), pd.Timestamp(fim))
    eixos[-1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%m/%Y'))
    eixos[-1].xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=(1, 4, 7, 10)))
    nome = CIDADES[cidade]['nome']
    papel = 'validação' if cidade in cidades_por_papel('validacao') else 'treino'
    fig.suptitle(f'{nome} ({papel}) · casos por semana (escala logarítmica) e limiares do MEM\n'
                 'Nas linhas "Previsto x sem. antes", a previsão do modelo de quantis feita x semanas antes para aquela '
                 'semana, com a faixa de 80%;\no que aconteceu aparece em cinza para comparação.',
                 x=0.06, y=0.98, ha='left', fontsize=10, color=TINTA)
    legenda = [plt.Line2D([], [], color=TINTA, linewidth=2), plt.Line2D([], [], color=MUDO, linewidth=1.2),
               plt.Line2D([], [], color=COR_VARIANTE['A'], linewidth=2),
               plt.Rectangle((0, 0), 1, 1, color=COR_VARIANTE['A'], alpha=0.18, linewidth=0),
               plt.Line2D([], [], color=COR_NIVEL[1], linewidth=1.2, linestyle='--'),
               plt.Line2D([], [], color=COR_NIVEL[2], linewidth=1.2, linestyle='--')]
    rotulos = ['casos (aconteceu)', 'casos (para comparação)', 'previsto (mediana)', 'faixa de 80%',
               'limiar do amarelo (pré-epidêmico)', 'limiar do vermelho (epidêmico)']
    fig.legend(legenda, rotulos, ncol=6, frameon=False, fontsize=9, labelcolor=TINTA_SEC, loc='lower left',
               bbox_to_anchor=(0.05, 0), handlelength=2.5)
    fig.subplots_adjust(left=0.06, right=0.98, top=0.88, bottom=0.08, hspace=0.35)
    caminho_fig = os.path.join(PASTA_FIGURAS, f'casos_{cidade}.png')
    fig.savefig(caminho_fig, dpi=150, facecolor=FUNDO)
    plt.close(fig)
    return caminho_fig


# --------------------------------------------------------------- execução

def run_experimento(processos=PROCESSOS, resumo=False):
    id_ = id_dados_processados()
    fim = dados('A')[0]['data_iniSE'].max().to_period('M').strftime('%Y-%m')
    unidades = rodar_previsoes(id_, fim, processos)
    os.makedirs(PASTA_FIGURAS, exist_ok=True)

    semanas, episodios_, cortes_todos, alertas_h = [], [], [], []
    for variante in VARIANTES_NIVEIS:
        t = tabela_longa(id_, variante, unidades)
        cortes = escolher_cortes(t)
        t = prever_nivel(t, cortes)
        cortes_todos.append(cortes.assign(variante=variante))
        avaliada = t[(t['data_iniSE'] >= INICIO_AVALIACAO) & t['nivel_futuro'].notna() & t['nivel_corte'].notna()]
        for (conjunto, h), g in avaliada.groupby(['conjunto', 'h']):
            for metodo, prev in [('modelo', g['nivel_previsto']), ('modelo_cortes', g['nivel_corte']),
                                 ('persistencia', g['faixa'])]:
                semanas.append({'variante': variante, 'conjunto': conjunto, 'h': h, 'metodo': metodo,
                                'semanas_vermelhas': (g['nivel_futuro'] == 2).mean(),
                                'semanas_amarelas': (g['nivel_futuro'] == 1).mean(),
                                **metricas_semana(g['nivel_futuro'], prev, g['faixa'])})
        linhas_ep, alertas = episodios_vermelho(t, variante)
        episodios_ += linhas_ep
        t = alertas_por_antecedencia(t, alertas)
        alertas_h += resumo_alertas_por_antecedencia(t, variante)
        for cidade, inicio, fim_ex in (EXEMPLOS if variante in VARIANTES_QUADRADINHOS else []):
            logging.info(f"Figura: {grafico_quadradinhos(t, variante, cidade, inicio, fim_ex)}")
            if variante == 'D' and os.path.exists(ARQUIVO_PREVISOES_PASSADAS):
                logging.info(f"Figura: {grafico_casos(cidade, inicio, fim_ex)}")

    semanas = pd.DataFrame(semanas)
    semanas.round(3).to_csv(ARQUIVO_SEMANAS, index=False)
    pd.DataFrame(episodios_).round(3).to_csv(ARQUIVO_EPISODIOS, index=False)
    pd.concat(cortes_todos).to_csv(ARQUIVO_CORTES, index=False)
    pd.DataFrame(alertas_h).round(3).to_csv(ARQUIVO_ALERTAS_H, index=False)
    if resumo:  # gráficos de comparação das definições A e B (python -m src.experimento_niveis --resumo)
        logging.info(f"Figura: {grafico_comparacao(semanas[semanas['variante'].isin(['A', 'B'])])}")
        logging.info(f"Figura: {grafico_alertas(pd.DataFrame(episodios_).query('variante in [\"A\", \"B\"]'))}")
    pd.set_option('display.width', 250)
    print(semanas[semanas['conjunto'] == 'validacao_cruzada'].round(3).to_string(index=False))
    print(pd.DataFrame(episodios_).round(3).to_string(index=False))
    print(pd.DataFrame(alertas_h).round(3).to_string(index=False))


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index('--processos') + 1]) if '--processos' in sys.argv else PROCESSOS
    from src import experimento_niveis
    experimento_niveis.run_experimento(n, resumo='--resumo' in sys.argv)
