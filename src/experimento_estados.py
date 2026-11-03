"""
Experimento: o painel ajudaria o gestor a mobilizar e desmobilizar recursos na hora certa?

Pergunta: prevendo a probabilidade de o município estar no nível alto daqui a 1 a 4
semanas (src/estados.py, src/modelos/estado_lightgbm.py), o painel avisaria as epidemias
antes de elas começarem, com quanta antecedência e com quantos alarmes falsos?

Previsões: walk-forward com retreino a cada 3 meses desde 2015, por validação cruzada por
município (5 grupos de 20 dos 100 de treino) e nos 15 municípios de validação (modelo
treinado com os 100). As previsões de 2015 a 2018 servem só para escolher os pontos de
corte; a avaliação é de 2019 em diante.

Avisos de mobilização (semanas em que o município está no nível normal), com a maior das
probabilidades de nível alto em S+1 a S+4:
  - alerta: probabilidade >= menor corte em que, no passado, pelo menos metade dos alarmes
    foi correta (1 alarme correto para cada falso, com alarme e correto definidos como na
    avaliação, abaixo);
  - atenção: probabilidade acima do normal (a frequência, no passado, de entrar no nível
    alto em até 4 semanas), mas abaixo do corte do alerta.
Os cortes são escolhidos a cada trimestre só com as previsões anteriores dos municípios de
treino (validação cruzada) e aplicados ao trimestre seguinte, como o painel faria.

Comparações (avisos na mesma situação, nível normal):
  - persistência: nunca avisa antes; reconhece a epidemia só na semana em que ela começa;
  - regra simples: casos subindo há 2 semanas e acima da metade do limiar;
  - alerta do InfoDengue (nível laranja ou vermelho), só como comparação: não entra em
    nenhum modelo.

Métricas por episódio (src/estados.episodios):
  - epidemias avisadas: % dos episódios com aviso nas 4 semanas antes do início;
  - antecedência: semanas entre o primeiro aviso dessas 4 semanas e o início;
  - alarmes: sequências de semanas seguidas com aviso; corretos se um episódio começa até 4
    semanas depois do fim da sequência; falsos por município por ano e % de corretos;
  - desmobilização: % dos fins de episódio com probabilidade de nível alto em S+2 abaixo de
    50% nas 2 semanas antes do retorno ao normal, e avisos prematuros (com o episódio
    continuando por 3 semanas ou mais) por episódio.
Também, por semana: AUC da probabilidade de entrar no nível alto, entre as semanas normais.

Definição principal: percentil 90% (PERCENTIL_ALTO); sensibilidade: 80%.

Saídas:
  reports/estados_episodios.csv     métricas por episódio e alarmes, por definição, conjunto e método
  reports/estados_cortes.csv        cortes de atenção e alerta escolhidos em cada trimestre
  reports/estados_semanas.csv       AUC e frequência de entrada no nível alto, por horizonte

Uso:
  python -m src.experimento_estados
"""
import functools
import logging
import os
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from src.cidades import cidades_por_papel
from src.estados import PERCENTIL_ALTO, PERCENTIL_SENSIBILIDADE, adicionar_estados, episodios
from src.experimento_generalizacao import grupos_de_municipios
from src.modelos.estado_lightgbm import EstadoLightGBM
from src.snapshot import id_dados_processados
from src.train import HORIZONTES, PRIMEIRO_ANO_TESTE, SEMANAS_INSTAVEIS, carregar, linhas_validas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PERCENTIS = [PERCENTIL_ALTO, PERCENTIL_SENSIBILIDADE]
INICIO_AVALIACAO = '2019-01-01'
MESES_POR_RETREINO = 3
JANELA_AVISO = 4            # semanas antes do início de um episódio em que um aviso conta
PRECISAO_ALERTA = 0.5       # alarmes corretos >= falsos
CORTES = np.round(np.arange(0.05, 0.96, 0.01), 2)
PROCESSOS = 8
THREADS = 2
VERSAO_CACHE = 1
PASTA_CACHE = 'reports/cache/estados'
ARQUIVO_EPISODIOS = 'reports/estados_episodios.csv'
ARQUIVO_CORTES = 'reports/estados_cortes.csv'
ARQUIVO_SEMANAS = 'reports/estados_semanas.csv'


# --------------------------------------------------------------- previsões

@functools.lru_cache(maxsize=2)
def dados(percentil):
    return adicionar_estados(carregar('treino'), percentil), adicionar_estados(carregar('validacao'), percentil)


def caminho(id_, percentil, conjunto, inicio):
    return os.path.join(PASTA_CACHE, f'{id_}_v{VERSAO_CACHE}', f'p{round(percentil * 100)}', f'{conjunto}_{inicio}.parquet')


def executar_unidade(id_, percentil, conjunto, inicio):
    destino = caminho(id_, percentil, conjunto, inicio)
    if os.path.exists(destino):
        return
    treino, validacao = dados(percentil)
    if conjunto == 'final':
        tr_base, te_base = treino, validacao
    else:
        separado = grupos_de_municipios(treino['cidade'].unique())[int(conjunto[2:])]
        tr_base, te_base = treino[~treino['cidade'].isin(separado)], treino[treino['cidade'].isin(separado)]
    ini = pd.Period(inicio, freq='M').start_time
    fim = (pd.Period(inicio, freq='M') + MESES_POR_RETREINO).start_time
    partes = []
    with threadpool_limits(THREADS):
        for h in HORIZONTES:
            tr = linhas_validas(tr_base, h)
            tr = tr[tr[f'alto_h{h}'].notna() & (tr['data_iniSE'] + pd.Timedelta(weeks=h) < ini)]
            te = linhas_validas(te_base, h)
            te = te[te[f'alto_h{h}'].notna() & (te['data_iniSE'] >= ini) & (te['data_iniSE'] < fim)]
            if te.empty:
                continue
            modelo = EstadoLightGBM(threads=THREADS).treinar(tr, h)
            partes.append(pd.DataFrame({'cidade': te['cidade'].to_numpy(), 'data_iniSE': te['data_iniSE'].to_numpy(),
                                        'h': h, 'p_alto': modelo.prever(te, h)}))
    resultado = pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    resultado.to_parquet(destino + '.tmp', index=False)
    os.replace(destino + '.tmp', destino)


def rodar_previsoes(id_, fim, processos):
    inicios = [str(p) for p in pd.period_range(f'{PRIMEIRO_ANO_TESTE}-01', fim, freq='M')[::MESES_POR_RETREINO]]
    unidades = [(p, c, i) for p in PERCENTIS for c in [f'cv{k}' for k in range(5)] + ['final'] for i in inicios]
    pendentes = [u for u in unidades if not os.path.exists(caminho(id_, *u))]
    logging.info(f"{len(unidades)} unidades; {len(pendentes)} a rodar.")
    Parallel(n_jobs=processos, batch_size=1)(delayed(executar_unidade)(id_, *u) for u in pendentes)
    return unidades


def tabela_semanal(id_, percentil, unidades):
    """Uma linha por município e semana: estado atual, probabilidades em S+1 a S+4 e sinais de comparação."""
    prev = pd.concat([pd.read_parquet(caminho(id_, *u)) for u in unidades if u[0] == percentil], ignore_index=True)
    prob = prev.pivot_table(index=['cidade', 'data_iniSE'], columns='h', values='p_alto')
    prob.columns = [f'p_alto_h{h}' for h in prob.columns]
    treino, validacao = dados(percentil)
    base = pd.concat([treino, validacao], ignore_index=True)
    colunas = ['cidade', 'data_iniSE', 'alto', 'razao_limiar', 'var_log_1', 'var_log_2', 'nivel']
    t = base[colunas].merge(prob.reset_index(), on=['cidade', 'data_iniSE'], how='left')
    t['conjunto'] = np.where(t['cidade'].isin(list(cidades_por_papel('validacao'))), 'validacao_final', 'validacao_cruzada')
    t['p_max'] = t[[f'p_alto_h{h}' for h in HORIZONTES]].max(axis=1)
    # Entra no nível alto em alguma das 4 semanas seguintes (para escolher os cortes)
    futuro = pd.concat([t.groupby('cidade')['alto'].shift(-k) for k in range(1, 5)], axis=1)
    t['entra_4sem'] = futuro.max(axis=1, skipna=False)
    t['regra'] = (t['var_log_1'] > 0) & (t['var_log_2'] > t['var_log_1']) & (t['razao_limiar'] >= np.log(0.5))
    t['infodengue'] = t['nivel'] >= 3
    return t.sort_values(['cidade', 'data_iniSE']).reset_index(drop=True)


# --------------------------------------------------------------- cortes escolhidos com o passado

def escolher_cortes(t, estado='alto', atraso=0):
    """Corte de atenção e de alerta para cada trimestre, só com as previsões anteriores (validação cruzada).

    Atenção: frequência, no passado, de entrar no nível alto em até 4 semanas a partir de uma
    semana normal. Alerta: menor corte cujos alarmes do passado foram corretos pelo menos
    PRECISAO_ALERTA das vezes (com ao menos 20 alarmes), com alarme e correto definidos como na
    avaliação; só entram alarmes cujo resultado já era conhecido no início do trimestre.

    'estado' é a coluna com o estado conhecido na semana do alarme ('alto', ou o estado de
    semanas antes, quando os dados recentes estão atrasados); 'atraso' (semanas) adia o
    momento em que o resultado de um alarme passa a ser conhecido.
    """
    cv = t[t['conjunto'] == 'validacao_cruzada'].copy()
    semanas_normais = cv[(cv[estado] == False) & cv['p_max'].notna() & cv['entra_4sem'].notna()]  # noqa: E712
    normal = cv[estado] == False  # noqa: E712
    alarmes_por_corte = {}
    for c in CORTES:
        cv['_sinal'] = normal & (cv['p_max'] >= c)
        alarmes_por_corte[c] = alarmes(cv, '_sinal', desde=f'{PRIMEIRO_ANO_TESTE}-01-01', atraso=atraso)
    linhas = []
    for trimestre in pd.period_range(INICIO_AVALIACAO[:7], t['data_iniSE'].max(), freq='Q'):
        # O resultado de um alarme só é conhecido 4 semanas depois do seu fim
        limite = trimestre.start_time - pd.Timedelta(weeks=JANELA_AVISO + atraso)
        y = semanas_normais.loc[semanas_normais['data_iniSE'] < limite, 'entra_4sem'].to_numpy(bool)
        alerta = np.nan
        for c in CORTES:
            a = alarmes_por_corte[c]
            a = a[a['fim'] < limite]
            if len(a) >= 20 and a['correto'].mean() >= PRECISAO_ALERTA:
                alerta = c
                break
        linhas.append({'trimestre': str(trimestre), 'corte_atencao': round(y.mean(), 3), 'corte_alerta': alerta,
                       'semanas_passado': len(y)})
    return pd.DataFrame(linhas)


def aplicar_cortes(t, cortes, estado='alto'):
    tri = t['data_iniSE'].dt.to_period('Q').astype(str)
    c = cortes.set_index('trimestre')
    t['corte_atencao'] = tri.map(c['corte_atencao'])
    t['corte_alerta'] = tri.map(c['corte_alerta'])
    normal = t[estado] == False  # noqa: E712
    t['modelo_alerta'] = normal & (t['p_max'] >= t['corte_alerta'])
    t['modelo_atencao_ou_alerta'] = normal & (t['p_max'] >= t['corte_atencao'])
    t['regra'] = normal & t['regra']
    t['infodengue'] = normal & t['infodengue']
    return t


# --------------------------------------------------------------- métricas por episódio

def alarmes(t, sinal, desde=INICIO_AVALIACAO, atraso=0):
    """Alarmes de um sinal: sequências de semanas seguidas com sinal (início, fim, correto).

    Um alarme é correto se um episódio de nível alto começa durante ele ou até JANELA_AVISO
    semanas depois do seu fim. Com dados atrasados ('atraso' semanas), também conta o episódio
    que começou até atraso-1 semanas antes do alarme, quando os dados ainda não o mostravam.
    As semanas mais recentes (estado ainda incerto) ficam de fora.
    """
    linhas = []
    for cidade, g in t.groupby('cidade', sort=False):
        g = g.iloc[:-SEMANAS_INSTAVEIS]
        datas = g['data_iniSE'].to_numpy()
        s = g[sinal].to_numpy(bool) & (g['data_iniSE'] >= desde).to_numpy() & g['p_max'].notna().to_numpy()
        inicios = [i for i, _ in episodios(g['alto'].fillna(False).to_numpy())]
        i = 0
        while i < len(s):
            if s[i]:
                j = i
                while j + 1 < len(s) and s[j + 1]:
                    j += 1
                linhas.append({'cidade': cidade, 'inicio': datas[i], 'fim': datas[j],
                               'correto': any(i - atraso < e <= j + JANELA_AVISO for e in inicios)})
                i = j + 1
            else:
                i += 1
    return pd.DataFrame(linhas, columns=['cidade', 'inicio', 'fim', 'correto'])


def avaliar(t, sinal):
    """Epidemias avisadas, antecedência e alarmes falsos de um sinal de mobilização (2019 em diante)."""
    avisadas, antecedencias, n_episodios, municipio_anos = 0, [], 0, 0
    for cidade, g in t.groupby('cidade', sort=False):
        g = g.iloc[:-SEMANAS_INSTAVEIS]  # semanas recentes: estado ainda incerto
        avaliada = (g['data_iniSE'] >= INICIO_AVALIACAO).to_numpy() & g['p_max'].notna().to_numpy()
        s = g[sinal].to_numpy(bool) & avaliada
        for e, _ in episodios(g['alto'].fillna(False).to_numpy()):
            if e - JANELA_AVISO < 0 or not avaliada[e - JANELA_AVISO:e].all():
                continue
            n_episodios += 1
            janela = np.flatnonzero(s[e - JANELA_AVISO:e])
            if len(janela):
                avisadas += 1
                antecedencias.append(JANELA_AVISO - janela[0])
        municipio_anos += avaliada.sum() / 52.18
    a = alarmes(t, sinal)
    return {'episodios': n_episodios,
            'epidemias_avisadas': avisadas / n_episodios if n_episodios else np.nan,
            'antecedencia_mediana': float(np.median(antecedencias)) if antecedencias else np.nan,
            'antecedencia_media': float(np.mean(antecedencias)) if antecedencias else np.nan,
            'alarmes': len(a),
            'alarmes_corretos': a['correto'].mean() if len(a) else np.nan,
            'alarmes_falsos_por_municipio_ano': (~a['correto']).sum() / municipio_anos}


def avaliar_desmobilizacao(t):
    """Fins de episódio antecipados e avisos prematuros (probabilidade de nível alto em S+2 abaixo de 50%)."""
    fins, antecipados, prematuros = 0, 0, 0
    for cidade, g in t.groupby('cidade', sort=False):
        g = g.iloc[:-SEMANAS_INSTAVEIS]
        avaliada = (g['data_iniSE'] >= INICIO_AVALIACAO).to_numpy() & g['p_alto_h2'].notna().to_numpy()
        sai = (g['p_alto_h2'] < 0.5).to_numpy() & (g['alto'] == True).to_numpy()  # noqa: E712
        for i, f in episodios(g['alto'].fillna(False).to_numpy()):
            if f + 1 >= len(g) or not avaliada[max(i, f - 1):f + 1].all():
                continue
            fins += 1
            antecipados += sai[max(i, f - 1):f + 1].any()
            prematuros += sai[i:max(i, f - 2)].sum()
    return {'fins_de_episodio': fins, 'fins_antecipados': antecipados / fins if fins else np.nan,
            'avisos_prematuros_por_episodio': prematuros / fins if fins else np.nan}


def auc_entrada(t):
    linhas = []
    for conjunto, g in t[(t['data_iniSE'] >= INICIO_AVALIACAO) & (t['alto'] == False)].groupby('conjunto'):  # noqa: E712
        for h in HORIZONTES:
            x = g[[f'p_alto_h{h}']].join(t['alto'].groupby(t['cidade']).shift(-h).rename('futuro')).dropna()
            linhas.append({'conjunto': conjunto, 'h': h, 'semanas_normais': len(x),
                           'entram_no_alto': x['futuro'].astype(bool).mean(),
                           'auc': roc_auc_score(x['futuro'].astype(bool), x[f'p_alto_h{h}'])})
    return pd.DataFrame(linhas)


def run_experimento(processos=PROCESSOS):
    id_ = id_dados_processados()
    fim = dados(PERCENTIL_ALTO)[0]['data_iniSE'].max().to_period('M').strftime('%Y-%m')
    unidades = rodar_previsoes(id_, fim, processos)

    resultados, cortes_todos, semanas = [], [], []
    for percentil in PERCENTIS:
        t = tabela_semanal(id_, percentil, unidades)
        cortes = escolher_cortes(t)
        t = aplicar_cortes(t, cortes)
        cortes_todos.append(cortes.assign(percentil=percentil))
        semanas.append(auc_entrada(t).assign(percentil=percentil))
        for conjunto, g in t.groupby('conjunto'):
            for sinal, nome in [('modelo_alerta', 'Modelo: alerta'), ('modelo_atencao_ou_alerta', 'Modelo: atenção ou alerta'),
                                ('regra', 'Regra simples'), ('infodengue', 'Alerta do InfoDengue (comparação)')]:
                resultados.append({'percentil': percentil, 'conjunto': conjunto, 'metodo': nome, **avaliar(g, sinal)})
            resultados.append({'percentil': percentil, 'conjunto': conjunto, 'metodo': 'Modelo: desmobilização',
                               **avaliar_desmobilizacao(g)})

    pd.DataFrame(resultados).round(3).to_csv(ARQUIVO_EPISODIOS, index=False)
    pd.concat(cortes_todos).to_csv(ARQUIVO_CORTES, index=False)
    pd.concat(semanas).round(3).to_csv(ARQUIVO_SEMANAS, index=False)
    logging.info(f"Resultados salvos em {ARQUIVO_EPISODIOS}, {ARQUIVO_CORTES} e {ARQUIVO_SEMANAS}.")
    pd.set_option('display.width', 250)
    print(pd.DataFrame(resultados).round(3).to_string(index=False))


if __name__ == "__main__":
    n = int(sys.argv[sys.argv.index('--processos') + 1]) if '--processos' in sys.argv else PROCESSOS
    from src import experimento_estados
    experimento_estados.run_experimento(n)
