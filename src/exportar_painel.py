"""
Exporta os dados do painel estático (web/) em JSON: um arquivo por município, um índice e a
avaliação geral.

O painel parte do último nível confirmado: as 2 semanas mais recentes ainda estão incompletas
(reports/revisao_dados.csv), então a semana confirmada é a atual - 2. Todos os municípios têm o
nowcast do InfoDengue (os que não tinham foram substituídos, decisão 1); se algum o perder numa
atualização, a exportação avisa no log. A partir da semana confirmada, os modelos de produção
preveem a semana atual e as 4 seguintes (2 a 6 semanas à frente), como avaliado com dados
atrasados (decisões 16 e 17; experimento_niveis_robustez.py e experimento_casos_atraso.py):
  - níveis: NivelLightGBM (verde, amarelo, vermelho pelos limiares do MEM), nível mais provável;
  - casos aproximados: LightGBMQuantis (mediana e faixa de 80%);
  - alerta de mobilização (se o nível confirmado não é vermelho): maior probabilidade de
    vermelho de 2 a 4 semanas à frente da semana atual acima do corte mais recente escolhido
    com 2 semanas de atraso (reports/niveis_robustez_cortes.csv);
  - desmobilização (se o nível confirmado é vermelho): o nível mais provável 2 semanas à frente
    da semana atual deixa de ser vermelho.
Os modelos de produção são treinados aqui com os municípios de treino e todos os dados até as
semanas instáveis, como em train.py.

A seção Avaliação de cada município usa as previsões fora da amostra dos experimentos, no mesmo
modo do painel (2 semanas de atraso): níveis (caches de experimento_niveis e
experimento_niveis_robustez) e casos (cache de experimento_casos_atraso).

Saídas (web/public/dados/):
  indice.json             municípios, semana atual, cortes do alerta e situação de cada município
  avaliacao.json          métricas gerais (níveis, alerta, desmobilização, casos), com IC 95%
  municipios/<chave>.json série semanal, situação atual, previsões e avaliação do município

Uso: python -m src.exportar_painel   (depois de rodar os experimentos de níveis e de casos)
"""
import datetime
import json
import logging
import math
import os

import numpy as np
import pandas as pd

from src import experimento_casos_atraso as eca
from src import experimento_niveis as en
from src import experimento_niveis_robustez as enr
from src.cidades import CIDADES
from src.estados import MIN_CASOS_ALTO, MIN_CASOS_AMARELO
from src.experimento_atraso import adicionar_alvos
from src.mem import SEMANA_INICIO_TEMPORADA, limiares_mem, temporadas_do_municipio
from src.modelos.lightgbm_quantis import LightGBMQuantis
from src.modelos.nivel_lightgbm import NivelLightGBM
from src.snapshot import id_dados_processados
from src.train import HORIZONTES, SEMANAS_INSTAVEIS, linhas_validas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LACUNA = 2  # semanas incompletas: a confirmada é a atual - 2
ANTECEDENCIAS = [0, 1, 2, 3, 4]  # a partir da semana atual
HORIZONTES_PAINEL = [a + LACUNA for a in ANTECEDENCIAS]  # a partir da semana confirmada
ANTECEDENCIAS_ALERTA = [2, 3, 4]
INICIO_SERIE = '2015-01-01'
PASTA_SAIDA = 'web/public/dados'


# --------------------------------------------------------------- utilidades

def limpo(x, casas=None):
    """Valor pronto para JSON: NaN vira null; números com 'casas' decimais."""
    if x is None:
        return None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        if math.isnan(x):
            return None
        return round(float(x), casas) if casas is not None else float(x)
    if isinstance(x, (pd.Timestamp, datetime.date)):
        return x.strftime('%Y-%m-%d')
    return x


def lista(serie, casas=None):
    return [limpo(v, casas) for v in serie]


def gravar(caminho, dados):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, separators=(',', ':'))


def temporada_de(se):
    return se // 100 if se % 100 >= SEMANA_INICIO_TEMPORADA else se // 100 - 1


def tem_nowcast(g):
    """True se o InfoDengue publicou intervalo de nowcast em alguma das semanas recentes."""
    recentes = g.dropna(subset=['casos_est']).tail(SEMANAS_INSTAVEIS)
    return bool(((recentes['casos_est_max'] - recentes['casos_est_min']) > 0).any())


# --------------------------------------------------------------- modelos de produção

def treinar_producao(treino):
    niveis, casos = {}, {}
    for h in HORIZONTES_PAINEL:
        tr = linhas_validas(treino, min(h, max(HORIZONTES)))
        tn = tr[tr[f'faixa_h{h}'].notna()]
        niveis[h] = NivelLightGBM().treinar(tn, h)
        tc = tr[tr[f'target_h{h}'].notna()]
        casos[h] = LightGBMQuantis().treinar(tc, h)
        logging.info(f"Produção H+{h}: níveis com {len(tn)} semanas, casos com {len(tc)} "
                     f"(até {tc['data_iniSE'].max():%d/%m/%Y}).")
    return niveis, casos


def corte_alerta_atual():
    """Corte do alerta mais recente escolhido com 2 semanas de atraso: (corte, trimestre)."""
    c = pd.read_csv(enr.ARQUIVO_CORTES)
    c = c[(c['lacuna'] == LACUNA) & c['corte_alerta'].notna()].sort_values('trimestre')
    return float(c['corte_alerta'].iloc[-1]), c['trimestre'].iloc[-1]


def limiares_temporadas(g, temporadas):
    """Limiares MEM (em casos por semana) das temporadas pedidas, com as temporadas anteriores a cada uma."""
    pop = CIDADES[g['cidade'].iloc[0]]['populacao']
    se = g['SE'].to_numpy()
    incidencia = g['casos_est'].to_numpy() * 1e5 / pop
    saida = []
    for t in temporadas:
        pre, epi = limiares_mem(list(temporadas_do_municipio(se, incidencia, ate_temporada=t).values()))
        saida.append({'temporada': f'{t}/{str(t + 1)[-2:]}', 'inicio_se': t * 100 + SEMANA_INICIO_TEMPORADA,
                      'pre_epidemico': limpo(max(pre * pop / 1e5, MIN_CASOS_AMARELO), 0),
                      'epidemico': limpo(max(epi * pop / 1e5, MIN_CASOS_ALTO), 0)})
    return saida


# --------------------------------------------------------------- situação atual

def situacao_atual(g, niveis, casos, corte):
    """Nível confirmado, semanas incompletas, previsões e alerta de um município (g ordenado por semana)."""
    atual, confirmada = g.iloc[-1], g.iloc[-1 - LACUNA]
    linha_c = g.iloc[[-1 - LACUNA]]
    previsoes = []
    for a, h in zip(ANTECEDENCIAS, HORIZONTES_PAINEL):
        p = niveis[h].prever(linha_c, h)[0]
        q = casos[h].prever(linha_c, h).iloc[0]
        previsoes.append({'semana': limpo(atual['data_iniSE'] + pd.Timedelta(weeks=a)), 'antecedencia': a,
                          'p_verde': limpo(p[0], 3), 'p_amarelo': limpo(p[1], 3), 'p_vermelho': limpo(p[2], 3),
                          'nivel': int(np.argmax(p)), 'casos': limpo(q['previsto'], 0),
                          'casos_inf': limpo(q['inferior'], 0), 'casos_sup': limpo(q['superior'], 0)})
    # Limiares da temporada de cada semana prevista (a temporada muda na semana 41; perto do fim do ano,
    # se_atual + a pode passar de 52, mas continua na mesma temporada)
    temporada = temporada_de(int(atual['SE']))
    limiares = limiares_temporadas(g, [temporada, temporada + 1])
    for x in previsoes:
        lim = limiares[temporada_de(int(atual['SE']) + x['antecedencia']) - temporada]
        x['limiar_amarelo'], x['limiar_vermelho'] = lim['pre_epidemico'], lim['epidemico']
    em_vermelho = confirmada['faixa'] == 2
    p_max = max(x['p_vermelho'] for x in previsoes if x['antecedencia'] in ANTECEDENCIAS_ALERTA)
    if em_vermelho:
        fim = next(x for x in previsoes if x['antecedencia'] == 2)['nivel'] != 2
        estado = 'fim_indicado' if fim else 'epidemia_continua'
    else:
        estado = 'alerta' if p_max >= corte else 'sem_alerta'
    recentes = [{'semana': limpo(r['data_iniSE']), 'se': int(r['SE']), 'notificados': limpo(r['casos'], 0),
                 'estimados': limpo(r['casos_est'], 0), 'estimados_min': limpo(r['casos_est_min'], 0),
                 'estimados_max': limpo(r['casos_est_max'], 0)} for _, r in g.iloc[-LACUNA:].iterrows()]
    return {
        'semana_atual': limpo(atual['data_iniSE']), 'se_atual': int(atual['SE']),
        'tem_nowcast': tem_nowcast(g), 'lacuna': LACUNA,
        'confirmada': {'semana': limpo(confirmada['data_iniSE']), 'se': int(confirmada['SE']),
                       'casos': limpo(confirmada['casos_est'], 0), 'notificados': limpo(confirmada['casos'], 0),
                       'nivel': limpo(confirmada['faixa'])},
        'recentes': recentes,
        'previsoes': previsoes,
        'alerta': {'estado': estado, 'p_vermelho_max': limpo(p_max, 3), 'corte': corte},
        'limiares': limiares,
    }


# --------------------------------------------------------------- avaliação

def niveis_fora_da_amostra(id_):
    """Nível previsto para cada semana-alvo, com antecedência a partir da semana de consulta."""
    p = enr.rodar_previsoes(id_, en.PROCESSOS)
    p = p[p['h'].isin(HORIZONTES_PAINEL)].copy()
    p['antecedencia'] = p['h'] - LACUNA
    p['data_alvo'] = p['data_iniSE'] + pd.to_timedelta(7 * p['h'], unit='D')
    p['nivel'] = p[['p0', 'p1', 'p2']].to_numpy().argmax(axis=1)
    return p.pivot_table(index=['cidade', 'data_alvo'], columns='antecedencia', values='nivel')


def casos_fora_da_amostra(id_):
    p = eca.previsoes(id_, lacuna=LACUNA)
    return p.pivot_table(index=['cidade', 'data_alvo'], columns='antecedencia',
                         values=['previsto', 'inferior', 'superior'])


def avaliacao_geral():
    """Métricas gerais para a seção Avaliação (só leitura dos resultados dos experimentos)."""
    r = pd.read_csv(enr.ARQUIVO_SAIDA)
    c = pd.read_csv(eca.ARQUIVO_SAIDA)
    alertas_h = pd.read_csv(en.ARQUIVO_ALERTAS_H)
    alertas_h = alertas_h[alertas_h['variante'] == 'D']

    def registros(df):
        return [{k: limpo(v, 3) for k, v in linha.items()} for linha in df.to_dict('records')]
    return {'niveis_robustez': registros(r), 'casos_atraso': registros(c),
            'alertas_por_antecedencia': registros(alertas_h.drop(columns='variante'))}


# --------------------------------------------------------------- exportação

def run_exportacao():
    id_ = id_dados_processados()
    treino, validacao = (adicionar_alvos(d, max(HORIZONTES_PAINEL)) for d in en.dados('D'))
    niveis, casos = treinar_producao(treino)
    corte, trimestre_corte = corte_alerta_atual()
    niveis_oos, casos_oos = niveis_fora_da_amostra(id_), casos_fora_da_amostra(id_)
    base = pd.concat([treino, validacao], ignore_index=True).sort_values(['cidade', 'data_iniSE'])
    # Recomeça a pasta dos municípios: quem saiu da lista (decisão 1) não deve continuar publicado
    pasta_municipios = os.path.join(PASTA_SAIDA, 'municipios')
    if os.path.isdir(pasta_municipios):
        for arquivo in os.listdir(pasta_municipios):
            if arquivo.endswith('.json'):
                os.remove(os.path.join(pasta_municipios, arquivo))

    indice = []
    for cidade, g in base.groupby('cidade', sort=True):
        info = CIDADES[cidade]
        atual = situacao_atual(g, niveis, casos, corte)
        s = g[g['data_iniSE'] >= INICIO_SERIE]
        semanas = s['data_iniSE']
        no = niveis_oos.loc[cidade].reindex(semanas) if cidade in niveis_oos.index.get_level_values(0) else None
        co = casos_oos.loc[cidade].reindex(semanas) if cidade in casos_oos.index.get_level_values(0) else None
        avaliacao = {
            'niveis': {str(a): lista(no[a]) if no is not None and a in no else [] for a in ANTECEDENCIAS},
            'casos': {str(a): {k: lista(co[(k, a)], 0) if co is not None and (k, a) in co else []
                               for k in ('previsto', 'inferior', 'superior')} for a in ANTECEDENCIAS},
        }
        dados = {
            'id': cidade, 'nome': info['nome'], 'uf': info['uf'], 'papel': info['papel'],
            'populacao': int(info['populacao']), **atual,
            'serie': {'semana': lista(semanas), 'se': lista(s['SE']), 'casos': lista(s['casos_est'], 0),
                      'notificados': lista(s['casos'], 0), 'nivel': lista(s['faixa']),
                      'limiar_amarelo': lista(s['limiar_amarelo'], 0),
                      'limiar_vermelho': lista(s['limiar_vermelho'], 0)},
            'avaliacao': avaliacao,
        }
        # As semanas incompletas não têm nível confirmado
        corte_serie = len(s) - LACUNA
        dados['serie']['nivel'] = dados['serie']['nivel'][:corte_serie] + [None] * LACUNA
        gravar(os.path.join(PASTA_SAIDA, 'municipios', f'{cidade}.json'), dados)
        indice.append({'id': cidade, 'nome': info['nome'], 'uf': info['uf'], 'papel': info['papel'],
                       'nivel_confirmado': atual['confirmada']['nivel'], 'alerta': atual['alerta']['estado'],
                       'tem_nowcast': atual['tem_nowcast']})

    semana_atual = base['data_iniSE'].max()
    gravar(os.path.join(PASTA_SAIDA, 'indice.json'), {
        'gerado_em': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'versao_dados': id_[:12],
        'semana_atual': limpo(semana_atual), 'semanas_instaveis_treino': SEMANAS_INSTAVEIS,
        'lacuna': LACUNA, 'corte_alerta': corte, 'trimestre_corte': trimestre_corte, 'municipios': indice})
    gravar(os.path.join(PASTA_SAIDA, 'avaliacao.json'), avaliacao_geral())
    sem = [m['nome'] for m in indice if not m['tem_nowcast']]
    if sem:
        logging.warning(f"Sem nowcast do InfoDengue ({len(sem)}): {', '.join(sem)}. As semanas recentes desses "
                        "municípios estão mais incompletas; substituí-los (scripts/substituir_sem_nowcast.py).")
    logging.info(f"Painel exportado em {PASTA_SAIDA}: {len(indice)} municípios, semana atual {semana_atual:%d/%m/%Y}.")


if __name__ == "__main__":
    run_exportacao()
