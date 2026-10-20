"""
Experimento: chance de cada nível pela distribuição de casos (quantis em grade) x classificador de níveis.

O painel mostra os casos aproximados (modelo de quantis) e o nível mais provável (classificador
NivelLightGBM), dois modelos que discordam em cerca de 10% das previsões. Aqui o modelo de quantis
ganha mais quantis (src/modelos/lightgbm_quantis_niveis.py) e a chance de cada nível sai da curva
prevista dos casos, lida nos limiares do MEM. Se for tão bom quanto o classificador, um modelo só dá
os casos, os níveis e o alerta, e eles nunca se contradizem. Variantes (VARIANTES):
  - grade: 19 quantis (5% a 95%), com as variáveis do modelo de casos;
  - clima: 5 quantis (10%, 30%, 50%, 70% e 90%), com as variáveis do classificador (também o clima
    de S-1 a S-4 e a distância aos dois limiares). Com as mesmas previsões, grades de 3 a 9 quantis
    deram o mesmo resultado que a de 19 (diferenças de décimos de ponto);
  - clima19: 19 quantis (5% a 95%) com as variáveis do classificador, para conferir a grade com clima:
    empatou com a de 5 (décimos de ponto) e tem os mesmos casos (10%, 50% e 90% são os mesmos modelos);
  - clima_lat e clima_latlon: a de produção mais a latitude (e a longitude) da sede do município, para a
    sazonalidade regional (a mesma semana do ano é inverno no Sul e temporada de chuvas no Norte):
    acertam um pouco mais as mudanças de nível, mas avisam menos epidemias, sobretudo nos municípios de
    validação; ficaram de fora.

Previsões: como em experimento_casos_atraso.py (walk-forward com retreino trimestral desde 2015,
validação cruzada por município em 5 grupos e validação final nos 15 municípios de validação), de 2
a 6 semanas à frente da semana confirmada: com 2 semanas de dados atrasados, a semana atual e as 4
seguintes, como no painel.

Limiares: os conhecidos na data da previsão. Quando a semana prevista já é da temporada seguinte
(começa na semana 41), o limiar novo é recalculado só com as temporadas completas até a semana
confirmada; o nível real continua sendo o dos limiares de cada temporada (src/estados.py).

Comparação com o classificador nas mesmas semanas e municípios, com IC 95% e diferença pareada por
bootstrap sobre municípios (como em experimento_niveis_robustez.py, lacuna de 2 semanas):
  - nível: acerto, acerto quando o nível muda, RPS (erro das chances dos três níveis em ordem;
    menor é melhor) e Brier do vermelho, da semana atual a 4 semanas à frente;
  - mobilização: o mesmo alerta (maior chance de vermelho de 2 a 4 semanas à frente), com o corte
    escolhido de novo para cada modelo, pelo mesmo critério e só com o passado;
  - desmobilização: nível mais provável em 2 semanas deixa o vermelho;
  - calibração: chance de vermelho prevista x frequência observada, por faixa de 10 pontos.

Resultado: a variante clima empata ou supera o classificador e passou a ser o modelo do painel
(decisão 18 do README): previsoes_producao() dá as suas previsões fora da amostra de 2 a 8 semanas à
frente da semana confirmada, usadas em experimento_niveis_robustez.py (atrasos de 0 a 4 semanas),
experimento_casos_atraso.py e exportar_painel.py.

Saídas: reports/niveis_quantis.csv, reports/niveis_quantis_calibracao.csv,
reports/niveis_quantis_cortes.csv; previsões em reports/cache/niveis_quantis

Fora do pipeline completo (as variantes levam cerca de 2h30 de treino): os resultados com os dados de
10/2026 estão em reports/niveis_quantis.csv. As previsões do modelo do painel (previsoes_producao) são
geradas quando experimento_niveis_robustez.py roda.

Uso: python -m src.experimento_niveis_quantis [--processos N]
"""
import functools
import logging
import os
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits

from src import experimento_niveis as en
from src import experimento_niveis_robustez as enr
from src.cidades import CIDADES, cidades_por_papel
from src.estados import MIN_CASOS_ALTO, MIN_CASOS_AMARELO
from src.experimento_atraso import adicionar_alvos
from src.experimento_generalizacao import grupos_de_municipios
from src.mem import SEMANA_INICIO_TEMPORADA, limiares_mem, temporadas_do_municipio
from src.modelos.lightgbm_quantis_niveis import GRADE, LightGBMQuantisNiveis, probabilidades_niveis
from src.modelos.nivel_lightgbm import FEATURES_NIVEIS
from src.snapshot import id_dados_processados
from src.train import FEATURES, HORIZONTES, PRIMEIRO_ANO_TESTE, linhas_validas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LACUNA = 2
ANTECEDENCIAS = [0, 1, 2, 3, 4]  # a partir da semana atual
HORIZONTES_Q = [a + LACUNA for a in ANTECEDENCIAS]  # a partir da semana confirmada
HORIZONTES_EXTRAS = [7, 8]  # só para o modelo de produção: atraso de até 4 semanas + 4 de antecedência
INICIO_AVALIACAO = '2019-01-01'
MESES_POR_RETREINO = 3
PROCESSOS, THREADS = 8, 2
N_BOOTSTRAP = 2000
SEMENTE = 42
VERSAO_CACHE = 1
PASTA_CACHE = 'reports/cache/niveis_quantis'
ARQUIVO_SAIDA = 'reports/niveis_quantis.csv'
ARQUIVO_CALIBRACAO = 'reports/niveis_quantis_calibracao.csv'
ARQUIVO_CORTES = 'reports/niveis_quantis_cortes.csv'
VARIANTES = {
    'grade': {'nome': 'Quantis: 19, variáveis do modelo de casos', 'grade': GRADE, 'features': FEATURES},
    'clima': {'nome': 'Quantis: 5, variáveis do classificador (com clima)',
              'grade': np.array([0.1, 0.3, 0.5, 0.7, 0.9]), 'features': FEATURES_NIVEIS},
    'clima19': {'nome': 'Quantis: 19, variáveis do classificador (com clima)', 'grade': GRADE,
                'features': FEATURES_NIVEIS},
    'clima_lat': {'nome': 'Quantis: 5, com clima e latitude', 'grade': np.array([0.1, 0.3, 0.5, 0.7, 0.9]),
                  'features': FEATURES_NIVEIS + ['latitude']},
    'clima_latlon': {'nome': 'Quantis: 5, com clima, latitude e longitude', 'grade': np.array([0.1, 0.3, 0.5, 0.7, 0.9]),
                     'features': FEATURES_NIVEIS + ['latitude', 'longitude']},
}
VARIANTE_PRODUCAO = 'clima'
METODOS = {'classificador': 'Classificador de níveis (anterior)', **{k: v['nome'] for k, v in VARIANTES.items()}}


def colunas_q(variante):
    return [f'q{round(100 * q):02d}' for q in VARIANTES[variante]['grade']]


# --------------------------------------------------------------- previsões

@functools.lru_cache(maxsize=1)
def dados():
    """Treino e validação com os níveis do MEM (variante D), os alvos de casos até 8 semanas e as coordenadas."""
    def preparar(df):
        df = adicionar_alvos(df, max(HORIZONTES_EXTRAS))
        df['latitude'] = df['cidade'].map(lambda c: CIDADES[c]['lat'])
        df['longitude'] = df['cidade'].map(lambda c: CIDADES[c]['lon'])
        return df
    treino, validacao = en.dados(enr.VARIANTE)
    return preparar(treino), preparar(validacao)


def caminho(id_, variante, conjunto, inicio):
    return os.path.join(PASTA_CACHE, f'{id_}_v{VERSAO_CACHE}', variante, f'{conjunto}_{inicio}.parquet')


def linhas(df, h):
    v = linhas_validas(df, min(h, max(HORIZONTES)))  # o alvo de fato é target_h<H>, filtrado abaixo
    return v[v[f'target_h{h}'].notna() & v[f'faixa_h{h}'].notna()]


def executar_unidade(id_, variante, conjunto, inicio, horizontes=HORIZONTES_Q, pasta=None):
    destino = caminho(id_, pasta or variante, conjunto, inicio)
    v = VARIANTES[variante]
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
        for h in horizontes:
            tr = linhas(tr_base, h)
            tr = tr[tr['data_iniSE'] + pd.Timedelta(weeks=h) < ini]
            te = linhas(te_base, h)
            te = te[(te['data_iniSE'] >= ini) & (te['data_iniSE'] < fim)]
            if te.empty:
                continue
            modelo = LightGBMQuantisNiveis(threads=THREADS, grade=v['grade'], features=v['features'])
            parte = pd.DataFrame(modelo.treinar(tr, h).prever_quantis(te, h), columns=colunas_q(variante))
            parte.insert(0, 'cidade', te['cidade'].to_numpy())
            parte.insert(1, 'data_iniSE', te['data_iniSE'].to_numpy())
            parte.insert(2, 'h', h)
            partes.append(parte)
    resultado = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    resultado.to_parquet(destino + '.tmp', index=False)
    os.replace(destino + '.tmp', destino)


def rodar_previsoes(id_, variante, processos, horizontes=HORIZONTES_Q, pasta=None):
    """Quantis previstos fora da amostra (roda as unidades que faltam); 'pasta' separa o cache de outros horizontes."""
    pasta = pasta or variante
    fim = dados()[0]['data_iniSE'].max().to_period('M').strftime('%Y-%m')
    inicios = [str(p) for p in pd.period_range(f'{PRIMEIRO_ANO_TESTE}-01', fim, freq='M')[::MESES_POR_RETREINO]]
    unidades = [(c, i) for c in [f'cv{k}' for k in range(5)] + ['final'] for i in inicios]
    pendentes = [u for u in unidades if not os.path.exists(caminho(id_, pasta, *u))]
    logging.info(f"{pasta}: {len(unidades)} unidades; {len(pendentes)} a rodar.")
    Parallel(n_jobs=processos, batch_size=1)(
        delayed(executar_unidade)(id_, variante, *u, horizontes, pasta) for u in pendentes)
    return pd.concat([pd.read_parquet(caminho(id_, pasta, *u)) for u in unidades], ignore_index=True)


def previsoes_producao(id_, processos=PROCESSOS):
    """Previsões fora da amostra do modelo do painel, de 2 a 8 semanas à frente da semana confirmada:
    cidade, data_iniSE, h, chance de cada nível (p0, p1, p2) e os quantis de casos (q10, q30, q50, q70, q90)."""
    q = pd.concat([rodar_previsoes(id_, VARIANTE_PRODUCAO, processos),
                   rodar_previsoes(id_, VARIANTE_PRODUCAO, processos, HORIZONTES_EXTRAS, f'{VARIANTE_PRODUCAO}_extra')],
                  ignore_index=True)
    treino, validacao = dados()
    return chances_quantis(q, pd.concat([treino, validacao], ignore_index=True), VARIANTE_PRODUCAO, quantis=True)


# --------------------------------------------------------------- limiares conhecidos e chance de cada nível

def temporada(se):
    se = np.asarray(se)
    return np.where(se % 100 >= SEMANA_INICIO_TEMPORADA, se // 100, se // 100 - 1)


def limiares_conhecidos(q, base):
    """Limiares da semana prevista com os dados até a semana confirmada (colunas la, lv).

    Na mesma temporada da semana confirmada, são os da própria temporada (calculados com as
    anteriores, já completas). Na temporada seguinte, o MEM é refeito só com as temporadas
    completas até a semana confirmada, como o painel faz.
    """
    b = base[['cidade', 'data_iniSE', 'SE', 'casos_est', 'limiar_amarelo', 'limiar_vermelho']]
    q = q.merge(b[['cidade', 'data_iniSE', 'SE']], on=['cidade', 'data_iniSE'], how='left')
    alvo = b.rename(columns={'data_iniSE': 'data_alvo', 'SE': 'se_alvo', 'limiar_amarelo': 'la',
                             'limiar_vermelho': 'lv'}).drop(columns='casos_est')
    q['data_alvo'] = q['data_iniSE'] + pd.to_timedelta(7 * q['h'], unit='D')
    q = q.merge(alvo, on=['cidade', 'data_alvo'], how='left')
    muda = temporada(q['se_alvo']) > temporada(q['SE'])
    series = {c: g.sort_values('data_iniSE') for c, g in b.groupby('cidade')}
    memo = {}
    novos = []
    for (cidade, data, se_alvo) in q.loc[muda, ['cidade', 'data_iniSE', 'se_alvo']].drop_duplicates().itertuples(False):
        g = series[cidade]
        g = g[g['data_iniSE'] <= data]
        pop = CIDADES[cidade]['populacao']
        t_alvo = int(temporada(se_alvo))
        temporadas = temporadas_do_municipio(g['SE'].to_numpy(), g['casos_est'].to_numpy() * 1e5 / pop,
                                             ate_temporada=max(t_alvo, PRIMEIRO_ANO_TESTE - 1))
        chave = (cidade, tuple(temporadas))
        if chave not in memo:
            pre, epi = limiares_mem(list(temporadas.values()))
            memo[chave] = (max(pre * pop / 1e5, MIN_CASOS_AMARELO), max(epi * pop / 1e5, MIN_CASOS_ALTO))
        novos.append((cidade, data, se_alvo, *memo[chave]))
    if novos:
        novos = pd.DataFrame(novos, columns=['cidade', 'data_iniSE', 'se_alvo', 'la_novo', 'lv_novo'])
        q = q.merge(novos, on=['cidade', 'data_iniSE', 'se_alvo'], how='left')
        q.loc[muda, 'la'] = q.loc[muda, 'la_novo']
        q.loc[muda, 'lv'] = q.loc[muda, 'lv_novo']
        q = q.drop(columns=['la_novo', 'lv_novo'])
    q['muda_temporada'] = muda
    return q


def chances_quantis(q, base, variante, quantis=False):
    """Previsões dos quantis no formato das do classificador: cidade, data_iniSE, h, p0, p1, p2 (e os quantis)."""
    q = limiares_conhecidos(q, base)
    q = q[q['la'].notna() & q['lv'].notna()].copy()
    p = probabilidades_niveis(q[colunas_q(variante)].to_numpy(), q['la'].to_numpy(), q['lv'].to_numpy(),
                              VARIANTES[variante]['grade'])
    q['p0'], q['p1'], q['p2'] = p[:, 0], p[:, 1], p[:, 2]
    return q[['cidade', 'data_iniSE', 'h', 'p0', 'p1', 'p2', 'muda_temporada'] + (colunas_q(variante) if quantis else [])]


# --------------------------------------------------------------- avaliação

def tabela_semanal(prev, base):
    """Uma linha por município, semana confirmada e antecedência: chances, nível previsto e o real."""
    real = base.melt(id_vars=['cidade', 'data_iniSE', 'faixa'], value_vars=[f'faixa_h{h}' for h in HORIZONTES_Q],
                     var_name='h', value_name='real')
    real['h'] = real['h'].str.split('_h').str[1].astype(int)
    t = prev.merge(real, on=['cidade', 'data_iniSE', 'h'], how='inner').dropna(subset=['real', 'faixa'])
    t = t[t['data_iniSE'] + pd.Timedelta(weeks=LACUNA) >= INICIO_AVALIACAO]
    t['antecedencia'] = t['h'] - LACUNA
    t['nivel'] = t[['p0', 'p1', 'p2']].to_numpy().argmax(axis=1)
    p_acum = t[['p0', 'p1']].to_numpy().cumsum(axis=1)
    o_acum = np.column_stack([t['real'] <= 0, t['real'] <= 1]).astype(float)
    t['rps'] = ((p_acum - o_acum) ** 2).sum(axis=1) / 2
    t['brier_vermelho'] = (t['p2'] - (t['real'] == 2)) ** 2
    return t


def componentes_semana(g):
    muda = g['real'] != g['faixa']
    return {'semanas': len(g), 'acertos': int((g['nivel'] == g['real']).sum()), 'semanas_muda': int(muda.sum()),
            'acertos_muda': int((g['nivel'][muda] == g['real'][muda]).sum()), 'rps': g['rps'].sum(),
            'brier_vermelho': g['brier_vermelho'].sum()}


def metricas_semana(c):
    return {'acerto': c['acertos'] / c['semanas'],
            'acerto_quando_muda': c['acertos_muda'] / c['semanas_muda'] if c['semanas_muda'] else np.nan,
            'rps': c['rps'] / c['semanas'], 'brier_vermelho': c['brier_vermelho'] / c['semanas']}


def calibracao(t, metodo):
    faixas = np.minimum((t['p2'] * 10).astype(int), 9)
    c = t.assign(faixa_p=faixas, veio=(t['real'] == 2)).groupby(['conjunto', 'faixa_p']).agg(
        semanas=('veio', 'size'), chance_media=('p2', 'mean'), frequencia=('veio', 'mean')).reset_index()
    c['faixa_p'] = c['faixa_p'].map(lambda k: f'{10 * k}-{10 * k + 10}%')
    return c.assign(metodo=METODOS[metodo])


def avaliar(prevs, base, rng):
    """Métricas de cada método, com a diferença método - classificador nos mesmos municípios."""
    linhas_saida, cortes, calib = [], [], []
    semanais = {m: tabela_semanal(p, base) for m, p in prevs.items()}
    emissao = {}
    for m, p in prevs.items():
        emissao[m] = enr.tabela_emissao(p, base, LACUNA)
        cortes.append(emissao[m].attrs['cortes'].assign(metodo=METODOS[m]))
    for m, t in semanais.items():
        t['conjunto'] = np.where(t['cidade'].isin(list(cidades_por_papel('validacao'))), 'validacao_final',
                                 'validacao_cruzada')
        calib.append(calibracao(t, m))

    def comparar(teste, comp, metricas):
        if comp['classificador'].empty:
            return
        for m in comp:
            ref = comp['classificador'] if m != 'classificador' else None
            for linha in enr.com_ic(comp[m], metricas, ref, rng):
                linhas_saida.append({'teste': teste, 'conjunto': conjunto, 'metodo': METODOS[m], **linha})

    for conjunto in ('validacao_cruzada', 'validacao_final'):
        papel = list(cidades_por_papel('validacao'))
        no_conjunto = (lambda d: d[d['cidade'].isin(papel)]) if conjunto == 'validacao_final' else \
            (lambda d: d[~d['cidade'].isin(papel)])
        for a in ANTECEDENCIAS:
            comp = {m: pd.DataFrame({c: componentes_semana(g) for c, g in
                                     no_conjunto(t[t['antecedencia'] == a]).groupby('cidade', sort=True)}).T
                    for m, t in semanais.items()}
            comparar(f'nivel_antecedencia_{a}', comp, metricas_semana)
        s = {m: no_conjunto(e) for m, e in emissao.items()}
        comp = {m: pd.DataFrame({c: enr.componentes_alerta(g, 'modelo_alerta', LACUNA)
                                 for c, g in s[m].groupby('cidade', sort=True)}).T for m in s}
        comparar('mobilizacao', comp, enr.metricas_alerta)
        comp = {m: pd.DataFrame({c: enr.componentes_desmobilizacao(g, 'saida_modelo', LACUNA)
                                 for c, g in s[m].groupby('cidade', sort=True)}).T for m in s}
        comparar('desmobilizacao', comp, enr.metricas_desmobilizacao)
    return pd.DataFrame(linhas_saida), pd.concat(cortes), pd.concat(calib)


def run_experimento(processos=PROCESSOS):
    id_ = id_dados_processados()
    treino, validacao = dados()
    base = pd.concat([treino, validacao], ignore_index=True)
    classificador = enr.rodar_previsoes(id_, processos)
    prevs = {'classificador': classificador[classificador['h'].isin(HORIZONTES_Q)][['cidade', 'data_iniSE', 'h', 'p0',
                                                                                     'p1', 'p2']]}
    for variante in VARIANTES:
        q = rodar_previsoes(id_, variante, processos)
        logging.info(f"Variante {variante}: {len(q)} previsões; convertendo em chances de cada nível...")
        prevs[variante] = chances_quantis(q, base, variante).drop(columns='muda_temporada')
    # Mesmas semanas, municípios e antecedências em todos os métodos
    chave = ['cidade', 'data_iniSE', 'h']
    comuns = prevs['classificador'][chave]
    for p in prevs.values():
        comuns = comuns.merge(p[chave], on=chave)
    prevs = {m: p.merge(comuns, on=chave) for m, p in prevs.items()}
    logging.info(f"{len(comuns)} previsões em comum.")
    r, cortes, calib = avaliar(prevs, base, np.random.default_rng(SEMENTE))
    colunas = ['teste', 'conjunto', 'metodo', 'metrica', 'valor', 'ic95_inf', 'ic95_sup',
               'dif_vs_comparacao', 'dif_ic95_inf', 'dif_ic95_sup', 'municipios']
    r = r[colunas].sort_values(['teste', 'conjunto', 'metrica', 'metodo'])
    r.round(4).to_csv(ARQUIVO_SAIDA, index=False)
    cortes.to_csv(ARQUIVO_CORTES, index=False)
    calib.round(4).to_csv(ARQUIVO_CALIBRACAO, index=False)
    pd.set_option('display.width', 250)
    print(r.round(4).to_string(index=False))


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index('--processos') + 1]) if '--processos' in sys.argv else PROCESSOS
    from src import experimento_niveis_quantis
    experimento_niveis_quantis.run_experimento(n)
