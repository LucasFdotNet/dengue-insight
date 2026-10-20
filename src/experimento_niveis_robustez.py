"""
Experimento: robustez dos níveis pelo MEM (definição D) e do alerta de mobilização.

Modelo: o do painel desde a decisão 18, quantis de casos com o clima, com a chance de cada nível
lida nos limiares (experimento_niveis_quantis.previsoes_producao). Comparação: o classificador de
níveis usado antes (src/modelos/nivel_lightgbm.py; previsões de experimento_niveis.py e as de 5 a 8
semanas, rodadas aqui), nas mesmas semanas e municípios. Os dois com walk-forward e retreino
trimestral, validação cruzada por município e validação final.

Três testes:

1. Desmobilização: no fim de cada episódio vermelho, o modelo indicou a saída do vermelho
   (nível mais provável em S+2 deixa de ser vermelho) nas 2 semanas antes da volta ao amarelo
   ou ao verde? Avisos prematuros: semanas do episódio, antes disso, em que ele indicou a saída.
   Comparação: regra simples (casos caindo há 2 semanas).
2. Atraso dos dados: em tempo real, as semanas mais recentes estão incompletas (a última semana
   ainda sobe cerca de 45% nos 12 dias seguintes, a de 2 semanas antes, 8%, e a de 4 semanas
   antes, 3%; reports/revisao_dados.csv). Como em experimento_atraso.py, a simulação descarta
   as últimas LACUNA semanas: na semana X, o último dado usado é o de X-LACUNA, inclusive para
   saber o nível atual, e a previsão para X+H vem do modelo de H+LACUNA semanas. Lacunas de 0 a
   4; 2: cenário realista (o do painel); 4: pior caso (o mesmo da decisão 12). Com atraso, um alarme também
   é correto se o vermelho começou até lacuna-1 semanas antes dele (os dados ainda não o
   mostravam), e há duas medidas de antecipação: antes do início do episódio e antes de os
   dados mostrarem o início (ou o fim, na desmobilização), que é quando o gestor saberia sem o
   modelo.
3. Intervalos de confiança de 95% por bootstrap sobre municípios (2.000 reamostragens), para o
   alerta, a desmobilização e o acerto do nível previsto, e para a diferença entre o modelo e a
   regra simples (ou a persistência), com os mesmos municípios em cada reamostragem. Nas linhas
   do classificador anterior, a diferença é classificador - modelo.

Saídas: reports/niveis_robustez.csv (teste, conjunto, lacuna, método, métrica, valor e IC 95%) e
reports/niveis_robustez_cortes.csv (corte do alerta do modelo por trimestre e lacuna; o painel usa o
da lacuna 2)

Uso: python -m src.experimento_niveis_robustez [--processos N]
"""
import logging
import os
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from src import experimento_estados as ee
from src import experimento_niveis as en
from src.cidades import cidades_por_papel
from src.estados import episodios
from src.snapshot import id_dados_processados

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

VARIANTE = 'D'
LACUNAS = [0, 1, 2, 3, 4]
CLASSIFICADOR = 'Classificador de níveis (anterior)'
HORIZONTES_EXTRAS = [h for h in range(1, en.HORIZONTE_MAXIMO + 1) if h > max(en.HORIZONTES_NIVEIS)]
N_BOOTSTRAP = 2000
SEMENTE = 42
JANELA_SAIDA = 2  # a saída do vermelho conta se indicada nas 2 últimas semanas do episódio
PASTA_CACHE = 'reports/cache/niveis_atraso'
ARQUIVO_SAIDA = 'reports/niveis_robustez.csv'
ARQUIVO_CORTES = 'reports/niveis_robustez_cortes.csv'  # corte do alerta por trimestre (o painel usa a lacuna 2)


# --------------------------------------------------------------- previsões

def caminho(id_, conjunto, inicio):
    return os.path.join(PASTA_CACHE, f'{id_}_v{en.VERSAO_CACHE}', VARIANTE, f'{conjunto}_{inicio}.parquet')


def rodar_previsoes(id_, processos):
    """Antecedências de 5 a 8 semanas (as de 2 a 4 vêm do cache de experimento_niveis.py)."""
    fim = en.dados(VARIANTE)[0]['data_iniSE'].max().to_period('M').strftime('%Y-%m')
    unidades_niveis = en.rodar_previsoes(id_, fim, processos)
    inicios = sorted({u[2] for u in unidades_niveis})
    conjuntos = [f'cv{k}' for k in range(5)] + ['final']
    extras = [(c, i) for c in conjuntos for i in inicios]
    pendentes = [u for u in extras if not os.path.exists(caminho(id_, *u))]
    logging.info(f"{len(extras)} unidades de 5 a 8 semanas; {len(pendentes)} a rodar.")
    Parallel(n_jobs=processos, batch_size=1)(
        delayed(en.executar_unidade)(id_, VARIANTE, c, i, HORIZONTES_EXTRAS, caminho(id_, c, i)) for c, i in pendentes)
    partes = [pd.read_parquet(en.caminho(id_, *u)) for u in unidades_niveis if u[0] == VARIANTE]
    partes += [pd.read_parquet(caminho(id_, *u)) for u in extras]
    prev = pd.concat(partes, ignore_index=True)
    return prev[prev['h'] >= min(en.HORIZONTES_NIVEIS)]


# --------------------------------------------------------------- tabela por semana de emissão

def tabela_emissao(prev, base, lacuna):
    """Uma linha por município e semana X em que o painel seria consultado, com o que se sabe nela.

    alto: nível real de X (para os episódios); alto_conhecido: nível de X-lacuna; p_max: maior
    probabilidade de vermelho em X+2 a X+4; nivel_hH: nível mais provável em X+H (H = 2 a 4),
    todos com os dados até X-lacuna.
    """
    p = prev.copy()
    p['antecedencia'] = p['h'] - lacuna
    p = p[p['antecedencia'].isin(en.HORIZONTES_NIVEIS)]
    p['data_iniSE'] = p['data_iniSE'] + pd.Timedelta(weeks=lacuna)  # semana de emissão
    p['nivel'] = p[['p0', 'p1', 'p2']].to_numpy().argmax(axis=1)
    largo = p.pivot_table(index=['cidade', 'data_iniSE'], columns='antecedencia', values=['p2', 'nivel'])
    largo.columns = [f'{v}_h{h}' for v, h in largo.columns]
    largo['p_max'] = largo[[f'p2_h{h}' for h in en.HORIZONTES_NIVEIS]].max(axis=1)

    s = base[['cidade', 'data_iniSE', 'faixa', 'razao_vermelho', 'var_log_1', 'var_log_2']
             + [f'faixa_h{h}' for h in en.HORIZONTES_NIVEIS]].sort_values(['cidade', 'data_iniSE']).copy()
    s['alto'] = (s['faixa'] == 2).where(s['faixa'].notna())
    g = s.groupby('cidade', sort=False)
    for c in ['faixa', 'razao_vermelho', 'var_log_1', 'var_log_2']:
        s[f'{c}_conhecido'] = g[c].shift(lacuna)
    s['alto_conhecido'] = (s['faixa_conhecido'] == 2).where(s['faixa_conhecido'].notna())
    s = s.merge(largo.reset_index(), on=['cidade', 'data_iniSE'], how='left')
    futuro = pd.concat([s.groupby('cidade')['alto'].shift(-k) for k in range(1, 5)], axis=1)
    s['entra_4sem'] = futuro.max(axis=1, skipna=False)
    s['regra'] = ((s['var_log_1_conhecido'] > 0) & (s['var_log_2_conhecido'] > s['var_log_1_conhecido'])
                  & (s['razao_vermelho_conhecido'] >= np.log(0.5)))
    s['infodengue'] = False
    s['conjunto'] = np.where(s['cidade'].isin(list(cidades_por_papel('validacao'))), 'validacao_final',
                             'validacao_cruzada')
    s = s.reset_index(drop=True)
    cortes = ee.escolher_cortes(s, estado='alto_conhecido', atraso=lacuna)
    s = ee.aplicar_cortes(s, cortes, estado='alto_conhecido')
    s.attrs['cortes'] = cortes.assign(lacuna=lacuna)
    # Desmobilização: o município está (até onde se sabe) no vermelho e a indicação é de saída em X+2
    no_vermelho = s['alto_conhecido'] == True  # noqa: E712
    s['saida_modelo'] = no_vermelho & (s['nivel_h2'] != 2) & s['nivel_h2'].notna()
    s['saida_regra'] = (no_vermelho & (s['var_log_1_conhecido'] < 0)
                        & (s['var_log_2_conhecido'] < s['var_log_1_conhecido']))
    return s


# --------------------------------------------------------------- componentes por município

def componentes_alerta(g, sinal, lacuna):
    """Contagens de um município para o alerta (sem lacuna, as mesmas de experimento_estados.avaliar)."""
    a = ee.alarmes(g, sinal, atraso=lacuna)  # descarta as semanas instáveis por conta própria
    g = g.iloc[:-ee.SEMANAS_INSTAVEIS]
    avaliada = (g['data_iniSE'] >= ee.INICIO_AVALIACAO).to_numpy() & g['p_max'].notna().to_numpy()
    s = g[sinal].to_numpy(bool) & avaliada
    n, avisadas, antes_dos_dados = 0, 0, 0
    for e, _ in episodios(g['alto'].fillna(False).to_numpy()):
        fim_janela = e + max(lacuna, 1)  # antes de os dados mostrarem o início (sem lacuna: antes do início)
        if e - ee.JANELA_AVISO < 0 or fim_janela > len(g) or not avaliada[e - ee.JANELA_AVISO:fim_janela].all():
            continue
        n += 1
        avisadas += s[e - ee.JANELA_AVISO:e].any()
        antes_dos_dados += s[e - ee.JANELA_AVISO:e + lacuna].any()
    return {'episodios': n, 'avisadas': avisadas, 'antes_dos_dados': antes_dos_dados, 'alarmes': len(a),
            'corretos': int(a['correto'].sum()), 'municipio_anos': avaliada.sum() / 52.18}


def metricas_alerta(c):
    return {'epidemias_avisadas': c['avisadas'] / c['episodios'] if c['episodios'] else np.nan,
            'avisadas_antes_dos_dados': c['antes_dos_dados'] / c['episodios'] if c['episodios'] else np.nan,
            'alarmes_corretos': c['corretos'] / c['alarmes'] if c['alarmes'] else np.nan,
            'alarmes_falsos_por_municipio_ano': (c['alarmes'] - c['corretos']) / c['municipio_anos']}


def componentes_desmobilizacao(g, sinal, lacuna):
    """Fins de episódio vermelho indicados nas últimas JANELA_SAIDA semanas e avisos prematuros.

    Com lacuna, também os fins indicados antes de os dados mostrarem a saída do vermelho (até a
    semana fim+lacuna, a última em que o último dado conhecido ainda é vermelho).
    """
    g = g.iloc[:-ee.SEMANAS_INSTAVEIS]
    avaliada = (g['data_iniSE'] >= ee.INICIO_AVALIACAO).to_numpy() & g['nivel_h2'].notna().to_numpy()
    sai = g[sinal].to_numpy(bool)
    fins, antecipados, antes_dos_dados, prematuros = 0, 0, 0, 0
    for i, f in episodios(g['alto'].fillna(False).to_numpy()):
        inicio_janela = max(i, f - JANELA_SAIDA + 1)
        if f + lacuna + 1 >= len(g) or not avaliada[inicio_janela:f + lacuna + 1].all():
            continue
        fins += 1
        antecipados += sai[inicio_janela:f + 1].any()
        antes_dos_dados += sai[inicio_janela:f + lacuna + 1].any()
        prematuros += sai[i:inicio_janela].sum()
    return {'fins': fins, 'antecipados': antecipados, 'antes_dos_dados': antes_dos_dados, 'prematuros': prematuros}


def metricas_desmobilizacao(c):
    return {'fins_indicados': c['antecipados'] / c['fins'] if c['fins'] else np.nan,
            'fins_indicados_antes_dos_dados': c['antes_dos_dados'] / c['fins'] if c['fins'] else np.nan,
            'avisos_prematuros_por_episodio': c['prematuros'] / c['fins'] if c['fins'] else np.nan}


def componentes_nivel(g, h):
    """Acerto do nível previsto em X+H com os dados até X-lacuna, contra a persistência do nível conhecido."""
    x = g[(g['data_iniSE'] >= ee.INICIO_AVALIACAO) & g[f'faixa_h{h}'].notna() & g[f'nivel_h{h}'].notna()
          & g['faixa_conhecido'].notna()]
    real, modelo, persist = x[f'faixa_h{h}'], x[f'nivel_h{h}'], x['faixa_conhecido']
    muda = real != persist
    return {'semanas': len(x), 'acertos': int((modelo == real).sum()), 'acertos_persist': int((persist == real).sum()),
            'semanas_muda': int(muda.sum()), 'acertos_muda': int((modelo[muda] == real[muda]).sum())}


def metricas_nivel(c):
    return {'acerto': c['acertos'] / c['semanas'], 'acerto_persistencia': c['acertos_persist'] / c['semanas'],
            'ganho_sobre_persistencia': (c['acertos'] - c['acertos_persist']) / c['semanas'],
            'acerto_quando_muda': c['acertos_muda'] / c['semanas_muda'] if c['semanas_muda'] else np.nan}


# --------------------------------------------------------------- bootstrap

def com_ic(comp, metricas, comp_ref=None, rng=None):
    """Métricas com IC 95% (bootstrap sobre municípios); com comp_ref, também a diferença pareada."""
    colunas = list(comp.columns)
    va = comp.to_numpy(float)
    vb = comp_ref.reindex(comp.index).to_numpy(float) if comp_ref is not None else None
    pontual = metricas(dict(zip(colunas, va.sum(axis=0))))
    ref = metricas(dict(zip(colunas, vb.sum(axis=0)))) if vb is not None else None
    amostras, difs = {k: [] for k in pontual}, {k: [] for k in pontual}
    for _ in range(N_BOOTSTRAP):
        idx = rng.integers(0, len(va), len(va))
        ma = metricas(dict(zip(colunas, va[idx].sum(axis=0))))
        mb = metricas(dict(zip(colunas, vb[idx].sum(axis=0)))) if vb is not None else None
        for k in pontual:
            amostras[k].append(ma[k])
            if mb is not None:
                difs[k].append(ma[k] - mb[k])
    linhas = []
    for k, v in pontual.items():
        linha = {'metrica': k, 'valor': v, 'ic95_inf': np.nanpercentile(amostras[k], 2.5),
                 'ic95_sup': np.nanpercentile(amostras[k], 97.5), 'municipios': len(va)}
        if ref is not None:
            linha.update({'dif_vs_comparacao': v - ref[k], 'dif_ic95_inf': np.nanpercentile(difs[k], 2.5),
                          'dif_ic95_sup': np.nanpercentile(difs[k], 97.5)})
        linhas.append(linha)
    return linhas


def avaliar_lacuna(s, lacuna, rng, s_classificador):
    linhas = []
    for conjunto, gc in s.groupby('conjunto'):
        cidades = gc.groupby('cidade', sort=True)
        cidades_c = s_classificador[s_classificador['conjunto'] == conjunto].groupby('cidade', sort=True)
        base = {'conjunto': conjunto, 'lacuna': lacuna}
        alerta = {m: pd.DataFrame({c: componentes_alerta(g, m, lacuna) for c, g in cidades}).T
                  for m in ('modelo_alerta', 'regra')}
        alerta['classificador'] = pd.DataFrame({c: componentes_alerta(g, 'modelo_alerta', lacuna)
                                                for c, g in cidades_c}).T
        for metodo, ref, nome in [('modelo_alerta', 'regra', 'Modelo: alerta de vermelho'),
                                  ('regra', None, 'Regra simples (subindo há 2 semanas)'),
                                  ('classificador', 'modelo_alerta', f'{CLASSIFICADOR}: alerta de vermelho')]:
            for linha in com_ic(alerta[metodo], metricas_alerta, alerta.get(ref) if ref else None, rng):
                linhas.append({**base, 'teste': 'mobilizacao', 'metodo': nome, **linha})
        desm = {m: pd.DataFrame({c: componentes_desmobilizacao(g, m, lacuna) for c, g in cidades}).T
                for m in ('saida_modelo', 'saida_regra')}
        desm['classificador'] = pd.DataFrame({c: componentes_desmobilizacao(g, 'saida_modelo', lacuna)
                                              for c, g in cidades_c}).T
        for metodo, ref, nome in [('saida_modelo', 'saida_regra', 'Modelo: nível previsto em S+2 deixa o vermelho'),
                                  ('saida_regra', None, 'Regra simples (caindo há 2 semanas)'),
                                  ('classificador', 'saida_modelo',
                                   f'{CLASSIFICADOR}: nível previsto em S+2 deixa o vermelho')]:
            for linha in com_ic(desm[metodo], metricas_desmobilizacao, desm.get(ref) if ref else None, rng):
                linhas.append({**base, 'teste': 'desmobilizacao', 'metodo': nome, **linha})
        for h in en.HORIZONTES_NIVEIS:
            comp = pd.DataFrame({c: componentes_nivel(g, h) for c, g in cidades}).T
            comp_c = pd.DataFrame({c: componentes_nivel(g, h) for c, g in cidades_c}).T
            for linha in com_ic(comp, metricas_nivel, rng=rng):
                linhas.append({**base, 'teste': f'nivel_{h}_semanas', 'metodo': 'Modelo e persistência', **linha})
            for linha in com_ic(comp_c, metricas_nivel, comp, rng):
                linhas.append({**base, 'teste': f'nivel_{h}_semanas', 'metodo': f'{CLASSIFICADOR} e persistência',
                               **linha})
    return linhas


def run_experimento(processos=en.PROCESSOS):
    from src import experimento_niveis_quantis as enq  # importa este módulo; aqui, para não haver ciclo
    id_ = id_dados_processados()
    chave = ['cidade', 'data_iniSE', 'h']
    modelo = enq.previsoes_producao(id_, processos)[chave + ['p0', 'p1', 'p2']]
    classificador = rodar_previsoes(id_, processos)[chave + ['p0', 'p1', 'p2']]
    # Mesmas semanas, municípios e antecedências nos dois
    comuns = modelo[chave].merge(classificador[chave], on=chave)
    modelo, classificador = modelo.merge(comuns, on=chave), classificador.merge(comuns, on=chave)
    logging.info(f"{len(comuns)} previsões em comum de {comuns['h'].min()} a {comuns['h'].max()} semanas.")
    treino, validacao = en.dados(VARIANTE)
    base = pd.concat([treino, validacao], ignore_index=True)
    rng = np.random.default_rng(SEMENTE)
    linhas, cortes = [], []
    for lacuna in LACUNAS:
        logging.info(f"Lacuna de {lacuna} semana(s)...")
        s = tabela_emissao(modelo, base, lacuna)
        s_c = tabela_emissao(classificador, base, lacuna)
        cortes.append(s.attrs['cortes'])
        linhas += avaliar_lacuna(s, lacuna, rng, s_c)
    pd.concat(cortes).to_csv(ARQUIVO_CORTES, index=False)
    r = pd.DataFrame(linhas)
    colunas = ['teste', 'conjunto', 'lacuna', 'metodo', 'metrica', 'valor', 'ic95_inf', 'ic95_sup',
               'dif_vs_comparacao', 'dif_ic95_inf', 'dif_ic95_sup', 'municipios']
    r = r[colunas].sort_values(['teste', 'conjunto', 'metodo', 'metrica', 'lacuna'])
    r.round(3).to_csv(ARQUIVO_SAIDA, index=False)
    pd.set_option('display.width', 250)
    print(r.round(3).to_string(index=False))


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index('--processos') + 1]) if '--processos' in sys.argv else en.PROCESSOS
    from src import experimento_niveis_robustez
    experimento_niveis_robustez.run_experimento(n)
