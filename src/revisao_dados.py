"""
Quanto os dados do InfoDengue mudam de uma coleta para outra?

Compara as fotos de data/snapshots/ (ver snapshot.py), cada uma com a seguinte. Para cada
semana, conta quantas semanas antes da última semana da foto mais antiga ela está e soma,
nos 115 municípios, os casos estimados (casos_est, com o nowcast do InfoDengue) e os
notificados (casos) nas duas fotos. A diferença mostra quanto as semanas recentes ainda
crescem com as notificações atrasadas, e até quantas semanas para trás isso acontece
(base para o descarte das semanas finais, decisão 3 do README).

Saída: reports/revisao_dados.csv (uma linha por par de fotos e semanas antes da última).

Uso:
  python -m src.revisao_dados
"""
import io
import logging
import os
import zipfile

import pandas as pd

from src.snapshot import PASTA_SNAPSHOTS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ARQUIVO_SAIDA = 'reports/revisao_dados.csv'
SEMANAS_COMPARADAS = 20


def ler_foto(data):
    with zipfile.ZipFile(os.path.join(PASTA_SNAPSHOTS, data, 'infodengue.zip')) as z:
        partes = []
        for nome in z.namelist():
            df = pd.read_csv(io.BytesIO(z.read(nome)), usecols=['data_iniSE', 'casos_est', 'casos'],
                             parse_dates=['data_iniSE'])
            partes.append(df.assign(cidade=os.path.basename(nome).replace('_raw.csv', '')))
    return pd.concat(partes, ignore_index=True)


def comparar(antes, depois):
    ultima = antes['data_iniSE'].max()
    m = antes.merge(depois, on=['cidade', 'data_iniSE'], suffixes=('_antes', '_depois'))
    m['semanas_antes_da_ultima'] = (ultima - m['data_iniSE']).dt.days // 7
    m = m[m['semanas_antes_da_ultima'] < SEMANAS_COMPARADAS]
    t = m.groupby('semanas_antes_da_ultima').agg(
        municipios=('cidade', 'nunique'),
        casos_est_antes=('casos_est_antes', 'sum'), casos_est_depois=('casos_est_depois', 'sum'),
        notificados_antes=('casos_antes', 'sum'), notificados_depois=('casos_depois', 'sum')).reset_index()
    t['mudanca_casos_est'] = t['casos_est_depois'] / t['casos_est_antes'] - 1
    t['mudanca_notificados'] = t['notificados_depois'] / t['notificados_antes'] - 1
    return t.assign(ultima_semana_antes=ultima.date())


def run_revisao():
    fotos = sorted(d for d in os.listdir(PASTA_SNAPSHOTS)
                   if os.path.exists(os.path.join(PASTA_SNAPSHOTS, d, 'infodengue.zip')))
    if len(fotos) < 2:
        logging.warning("É preciso ao menos duas fotos em data/snapshots/ para comparar.")
        return
    tabelas = []
    for antes, depois in zip(fotos, fotos[1:]):
        t = comparar(ler_foto(antes), ler_foto(depois))
        tabelas.append(t.assign(foto_antes=antes, foto_depois=depois))
        logging.info(f"{antes} -> {depois}: última semana {t['casos_est_antes'].iloc[0]:.0f} -> "
                     f"{t['casos_est_depois'].iloc[0]:.0f} casos estimados ({t['mudanca_casos_est'].iloc[0]:+.0%})")
    resultado = pd.concat(tabelas, ignore_index=True)
    colunas = ['foto_antes', 'foto_depois', 'ultima_semana_antes'] + [c for c in resultado.columns if c not in
                                                                     ('foto_antes', 'foto_depois', 'ultima_semana_antes')]
    resultado[colunas].round(4).to_csv(ARQUIVO_SAIDA, index=False)
    logging.info(f"Salvo: {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    run_revisao()
