"""
Substitui os municípios sem nowcast do InfoDengue por municípios com nowcast (decisão 1).

Por que: nos municípios sem nowcast, as semanas recentes têm só os casos já notificados e
estão bem mais incompletas que nos demais; o painel teria de tratá-los de outro jeito (partir
de uma semana mais antiga). Para que todos tenham o mesmo tratamento, o grupo decidiu trocá-los.

Sem nowcast: nenhuma das últimas SEMANAS_INSTAVEIS semanas com dado tem intervalo de nowcast
(casos_est_max > casos_est_min), como em src/exportar_painel.tem_nowcast.

Substituto: sorteado (semente fixa) entre os municípios elegíveis da mesma UF; se a UF não
tiver nenhum, entre os da mesma macrorregião. Elegível: mais de 100 mil habitantes (Censo
2022), não capital, fora da lista, a mais de 50 km da capital da UF (para evitar regiões
metropolitanas, como na etapa 2) e de qualquer município da lista e dos substitutos já
sorteados, e com nowcast.
O sorteio substitui os critérios por tamanho e por histórico de surtos da seleção original,
que na prática eram escolhas entre candidatos equivalentes.

Fontes: população do Censo 2022 (IBGE, SIDRA, tabela 4709), coordenadas das sedes
(github.com/kelvins/municipios-brasileiros) e a API do InfoDengue.

Saída: reports/substituicao_municipios.csv (elegíveis de cada vaga, com o sorteado) e, com
--aplicar, a troca em data/config/cidades.csv.

Uso: python -m scripts.substituir_sem_nowcast [--aplicar]
"""
import io
import logging
import math
import sys
import unicodedata

import numpy as np
import pandas as pd
import requests

from src.cidades import ARQUIVO_CIDADES
from src.ingestion import fetch_infodengue_data
from src.train import SEMANAS_INSTAVEIS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

URL_POPULACAO = 'https://apisidra.ibge.gov.br/values/t/4709/n6/all/v/93/p/2022'
URL_COORDENADAS = 'https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv'
POPULACAO_MINIMA = 100_000
DISTANCIA_MINIMA_KM = 50
SEMENTE = 42
ARQUIVO_SAIDA = 'reports/substituicao_municipios.csv'
MACRORREGIAO = {'1': 'Norte', '2': 'Nordeste', '3': 'Sudeste', '4': 'Sul', '5': 'Centro-Oeste'}


def distancia_km(a, b):
    (la1, lo1), (la2, lo2) = [(math.radians(x), math.radians(y)) for x, y in (a, b)]
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def chave(nome):
    s = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode().lower()
    return '_'.join(p for p in ''.join(c if c.isalnum() else ' ' for c in s).split())


def municipios_ibge():
    """Municípios com população (Censo 2022), UF, macrorregião e coordenadas da sede."""
    pop = pd.DataFrame(requests.get(URL_POPULACAO, timeout=120).json()[1:])
    pop = pd.DataFrame({'geocode': pop['D1C'].astype(int), 'nome_uf': pop['D1N'], 'populacao': pop['V'].astype(int)})
    pop['nome'] = pop['nome_uf'].str.rsplit(' - ', n=1).str[0]
    pop['uf'] = pop['nome_uf'].str.rsplit(' - ', n=1).str[1]
    coord = pd.read_csv(io.StringIO(requests.get(URL_COORDENADAS, timeout=120).text))
    coord = coord.rename(columns={'codigo_ibge': 'geocode', 'latitude': 'lat', 'longitude': 'lon'})
    m = pop.merge(coord[['geocode', 'lat', 'lon', 'capital']], on='geocode', how='left')
    m['regiao'] = m['geocode'].astype(str).str[0].map(MACRORREGIAO)
    return m.drop(columns='nome_uf')


_nowcast = {}


def tem_nowcast_geocode(geocode):
    if geocode not in _nowcast:
        df = fetch_infodengue_data(geocode, ey_start=2025)
        _nowcast[geocode] = tem_nowcast(df)
    return _nowcast[geocode]


def tem_nowcast(df):
    recentes = df.dropna(subset=['casos_est']).sort_values('SE').tail(SEMANAS_INSTAVEIS)
    return bool(((recentes['casos_est_max'] - recentes['casos_est_min']) > 0).any())


def sem_nowcast(lista):
    """Municípios da lista sem nowcast nos dados processados atuais (mesma regra do painel)."""
    return [c for c in lista['chave'] if not tem_nowcast(pd.read_csv(f'data/processed/{c}_processed.csv'))]


def elegiveis(alvo, ocupados, fora, capitais):
    c = alvo[(alvo['populacao'] > POPULACAO_MINIMA) & ~alvo['geocode'].isin(fora) & (alvo['capital'] != 1)].copy()
    c['dist_lista_km'] = [min(distancia_km((r['lat'], r['lon']), p) for p in ocupados) for _, r in c.iterrows()]
    c['dist_capital_km'] = [distancia_km((r['lat'], r['lon']), capitais[r['uf']]) for _, r in c.iterrows()]
    c = c[(c['dist_lista_km'] > DISTANCIA_MINIMA_KM) & (c['dist_capital_km'] > DISTANCIA_MINIMA_KM)]
    c['tem_nowcast'] = [tem_nowcast_geocode(g) for g in c['geocode']]
    return c.sort_values('geocode')


def run(aplicar=False):
    lista = pd.read_csv(ARQUIVO_CIDADES)
    removidos = sem_nowcast(lista)
    logging.info(f"Sem nowcast ({len(removidos)}): {', '.join(removidos)}")
    ibge = municipios_ibge()
    mantidos = lista[~lista['chave'].isin(removidos)]
    fora = set(lista['geocode'].astype(int))  # nem os mantidos nem os removidos
    ocupados = [(r['lat'], r['lon']) for _, r in mantidos.iterrows()]
    capitais = {r['uf']: (r['lat'], r['lon']) for _, r in ibge[ibge['capital'] == 1].iterrows()}
    rng = np.random.default_rng(SEMENTE)
    escolhidos, linhas = [], []
    for k in sorted(removidos):
        removido = lista[lista['chave'] == k].iloc[0]
        regiao = ibge.loc[ibge['geocode'] == removido['geocode'], 'regiao'].iloc[0]
        for escopo, alvo in [('UF', ibge[ibge['uf'] == removido['uf']]), ('macrorregião', ibge[ibge['regiao'] == regiao])]:
            c = elegiveis(alvo, ocupados, fora, capitais)
            ok = c[c['tem_nowcast']]
            if not ok.empty:
                break
        sorteado = ok.iloc[rng.integers(len(ok))]
        for _, r in c.iterrows():
            linhas.append({'substitui': k, 'uf_original': removido['uf'], 'escopo': escopo, 'geocode': r['geocode'],
                           'nome': r['nome'], 'uf': r['uf'], 'populacao': r['populacao'],
                           'dist_lista_km': round(r['dist_lista_km']), 'tem_nowcast': r['tem_nowcast'],
                           'sorteado': r['geocode'] == sorteado['geocode']})
        fora.add(int(sorteado['geocode']))
        ocupados.append((sorteado['lat'], sorteado['lon']))
        onde = 'da UF' if escopo == 'UF' else f"da macrorregião {regiao} (sem elegível na UF)"
        escolhidos.append({'chave': chave(sorteado['nome']), 'geocode': int(sorteado['geocode']),
                           'nome': sorteado['nome'], 'uf': sorteado['uf'], 'lat': sorteado['lat'],
                           'lon': sorteado['lon'], 'papel': removido['papel'], 'populacao': int(sorteado['populacao']),
                           'criterio': f"Treino nacional: sorteado entre os elegíveis {onde} com nowcast "
                                       f"(>100 mil hab., a >50 km da capital e dos já incluídos); substitui {removido['nome']} "
                                       f"({removido['uf']}), sem nowcast",
                           'substitui': k, 'elegiveis': len(ok)})
        logging.info(f"{removido['nome']} ({removido['uf']}) -> {sorteado['nome']} ({sorteado['uf']}), "
                     f"entre {len(ok)} elegíveis {onde}")
    pd.DataFrame(linhas).to_csv(ARQUIVO_SAIDA, index=False)
    novos = pd.DataFrame(escolhidos)
    print(novos[['substitui', 'chave', 'nome', 'uf', 'populacao', 'elegiveis']].to_string(index=False))
    if aplicar:
        saida = pd.concat([mantidos, novos.drop(columns=['substitui', 'elegiveis'])], ignore_index=True)
        saida.to_csv(ARQUIVO_CIDADES, index=False, encoding='utf-8', lineterminator='\n')
        logging.info(f"{ARQUIVO_CIDADES} atualizado ({len(saida)} municípios).")


if __name__ == '__main__':
    run(aplicar='--aplicar' in sys.argv)
