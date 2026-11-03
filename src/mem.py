"""
MEM (Moving Epidemic Method): limiares pré-epidêmico e epidêmico de cada município.

Reimplementação em Python do método de Vega et al. (2013, 2015), seguindo o código do
pacote R `mem` (funções memmodel, memtiming, calcular.map, calcular.optimo.criterio,
suavizado e iconfianza.geometrica; github.com/lozalojo/mem), com as escolhas que o
InfoDengue usa (AlertTools, R/infodengue_apply_mem.R e R/dengue-mem.R; ver
docs/referencias.md):

  - temporada da semana epidemiológica 41 à 40 do ano seguinte; as 10 temporadas mais
    recentes; temporadas sem nenhum caso ficam de fora;
  - período epidêmico de cada temporada (memtiming, método 2): a curva MAP dá, para cada
    duração r, a maior porcentagem dos casos da temporada concentrada em r semanas seguidas;
    a curva é suavizada (regressão local linear com núcleo normal, largura 1) e a duração
    escolhida é a última antes de a inclinação cair abaixo de 2,8 pontos percentuais;
  - limiar pré-epidêmico: limite superior do intervalo de confiança unilateral de 95% da
    média geométrica de todas as semanas anteriores aos períodos epidêmicos;
  - limiar epidêmico (intensidade "muito alta" no InfoDengue): o mesmo intervalo, com 95%,
    sobre todas as semanas dos períodos epidêmicos;
  - segundo passe: as temporadas cujo pico não passa do limiar pré-epidêmico são descartadas
    e o cálculo é refeito (deixa os limiares refletirem as temporadas com epidemia).
Os mínimos de casos (5 e 10) e o uso dos limiares por ano ficam em src/estados.py.

Validação (validar_contra_infodengue): com os dados de 2010 a 2022, a reimplementação é
comparada com os limiares publicados pelo InfoDengue (parameters/mem/mem_mun_2010_2022_BR.csv,
repositório AlertaDengueAnalise).
"""
import numpy as np
from scipy.stats import norm

SEMANA_INICIO_TEMPORADA = 41
MAX_TEMPORADAS = 10
CRITERIO_INCLINACAO = 2.8
NIVEL = 0.95


def suavizar(y, h=1.0):
    """Regressão local linear com núcleo normal (sm.regression do R com poly.index = 1), nos pontos 1..n."""
    y = np.asarray(y, dtype=float)
    x = np.arange(1, len(y) + 1, dtype=float)
    validos = ~np.isnan(y)
    xv, yv = x[validos], y[validos]
    if len(xv) < 2:
        return y
    saida = np.empty(len(x))
    for i, x0 in enumerate(x):
        w = np.exp(-0.5 * ((xv - x0) / h) ** 2)
        dx = xv - x0
        s0, s1, s2 = w.sum(), (w * dx).sum(), (w * dx * dx).sum()
        t0, t1 = (w * yv).sum(), (w * dx * yv).sum()
        det = s0 * s2 - s1 * s1
        saida[i] = (s2 * t0 - s1 * t1) / det if det > 1e-12 else t0 / s0
    return np.maximum(saida, 0)


def curva_map(temporada):
    """Para cada duração r (0..n): % máximo dos casos da temporada em r semanas seguidas e onde ocorre."""
    x = np.nan_to_num(np.asarray(temporada, dtype=float))
    n, total = len(x), x.sum()
    acumulado = np.concatenate([[0.0], np.cumsum(x)])
    linhas = [(0, 0.0, 0, 0)]
    for r in range(1, n + 1):
        somas = acumulado[r:] - acumulado[:-r]
        inicio = int(np.argmax(somas))
        linhas.append((r, 100 * somas[inicio] / total if total else 0.0, inicio, inicio + r - 1))
    return np.array(linhas)


def periodo_epidemico(temporada):
    """Início e fim (posições, inclusivos) do período epidêmico da temporada (memtiming, método 2)."""
    curva = curva_map(temporada)
    duracoes, porcentagem = curva[:, 0], curva[:, 1]
    inclinacao = np.diff(suavizar(porcentagem, 1.0))
    abaixo = duracoes[1:][inclinacao < CRITERIO_INCLINACAO]
    duracao = max(int(abaixo.min()) - 1, 1) if len(abaixo) else int(duracoes.max())
    linha = curva[curva[:, 0] == duracao][0]
    return int(linha[2]), int(linha[3])


def limite_superior_geometrico(valores, nivel=NIVEL):
    """Limite superior do IC unilateral da média geométrica (iconfianza.geometrica, colas = 1)."""
    v = np.asarray(valores, dtype=float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return np.nan
    deslocamento = 0.0 if np.all(v != 0) else 1.0
    lx = np.log(v + deslocamento)
    erro = lx.std(ddof=1) / np.sqrt(len(lx)) if len(lx) > 1 else 0.0
    return float(np.exp(lx.mean() + norm.ppf(nivel) * erro) - deslocamento)


def _limiares(temporadas):
    pre, epi = [], []
    for t in temporadas:
        ini, fim = periodo_epidemico(t)
        pre.extend(t[:ini])
        epi.extend(t[ini:fim + 1])
    return limite_superior_geometrico(pre), limite_superior_geometrico(epi)


def limiares_mem(temporadas):
    """(limiar pré-epidêmico, limiar epidêmico) a partir de uma lista de temporadas (arrays semanais).

    Usa as MAX_TEMPORADAS mais recentes com algum caso; segundo passe como no InfoDengue.
    """
    temporadas = [np.nan_to_num(np.asarray(t, dtype=float)) for t in temporadas]
    temporadas = [t for t in temporadas if t.sum() > 0][-MAX_TEMPORADAS:]
    if len(temporadas) < 2:
        return np.nan, np.nan
    pre, _ = _limiares(temporadas)
    com_epidemia = [t for t in temporadas if t.max() > pre]
    if len(com_epidemia) >= 2:
        temporadas = com_epidemia
    return _limiares(temporadas)


def temporadas_do_municipio(se, valores, ate_temporada=None):
    """Separa a série semanal em temporadas completas (semana 41 a 40); devolve {ano de início: array}.

    'ate_temporada': só temporadas que começam antes desse ano (as completas até a semana 40 dele).
    """
    ano, semana = np.asarray(se) // 100, np.asarray(se) % 100
    inicio = np.where(semana >= SEMANA_INICIO_TEMPORADA, ano, ano - 1)
    saida = {}
    for a in np.unique(inicio):
        if ate_temporada is not None and a >= ate_temporada:
            continue
        sel = inicio == a
        if sel.sum() >= 52:  # temporada completa
            saida[int(a)] = np.asarray(valores, dtype=float)[sel]
    return saida


def validar_contra_infodengue(caminho_infodengue):
    """Compara os limiares desta reimplementação (2010-2022) com os publicados pelo InfoDengue."""
    import pandas as pd
    from src.cidades import CIDADES

    ref = pd.read_csv(caminho_infodengue)
    linhas = []
    for cidade, info in CIDADES.items():
        r = ref[ref['municipio_geocodigo'] == int(info['geocode'])]
        if r.empty:
            continue
        d = pd.read_csv(f'data/raw/{cidade}_raw.csv', usecols=['SE', 'casos'])
        d = d[d['SE'] <= 202240].sort_values('SE')
        incidencia = d['casos'] * 1e5 / r['pop'].iloc[0]  # como o InfoDengue: notificados por 100 mil
        temporadas = temporadas_do_municipio(d['SE'], incidencia)
        pre, epi = limiares_mem(list(temporadas.values()))
        linhas.append({'cidade': cidade, 'pre_nosso': pre, 'pre_infodengue': r['inc_preseason'].iloc[0],
                       'epi_nosso': epi, 'epi_infodengue': r['inc_epidemico'].iloc[0]})
    return pd.DataFrame(linhas)


if __name__ == "__main__":
    import sys
    v = validar_contra_infodengue(sys.argv[1])
    for k in ('pre', 'epi'):
        razao = v[f'{k}_nosso'] / v[f'{k}_infodengue']
        print(f"{k}: correlação {np.corrcoef(np.log(v[f'{k}_nosso']), np.log(v[f'{k}_infodengue']))[0, 1]:.3f}; "
              f"razão nosso/InfoDengue: mediana {razao.median():.3f}, "
              f"{(razao.between(0.9, 1.1)).mean():.0%} dos municípios a menos de 10%")
    print(v.round(2).to_string(index=False))
