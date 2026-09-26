import os
import sys
import pandas as pd
import logging
from datetime import date
from io import StringIO
from src.cidades import CIDADES
from src.http_utils import get_com_retentativas

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

URL = "https://info.dengue.mat.br/api/alertcity"


def fetch_infodengue_data(geocode, ey_start=2010, ey_end=None):
    params = {
        "geocode": geocode,
        "disease": "dengue",
        "format": "csv",
        "ew_start": 1,
        "ew_end": 53,
        "ey_start": ey_start,
        "ey_end": ey_end or date.today().year
    }
    response = get_com_retentativas(URL, params, timeout=60, descricao=f"InfoDengue {geocode}")
    return pd.read_csv(StringIO(response.text))


def run_ingestion():
    os.makedirs('data/raw', exist_ok=True)
    falhas = []

    # Baixa a série inteira sempre: o InfoDengue revisa as semanas recentes (nowcast)
    for cidade, info in CIDADES.items():
        logging.info(f"Buscando dados de {info['nome']} ({info['geocode']})...")
        try:
            df = fetch_infodengue_data(info["geocode"])
        except Exception as e:
            logging.error(f"Erro ao buscar dados de {cidade}: {e}")
            falhas.append(cidade)
            continue
        if df.empty:
            logging.error(f"Sem dados retornados para {cidade}.")
            falhas.append(cidade)
            continue
        filepath = f"data/raw/{cidade}_raw.csv"
        df.to_csv(filepath, index=False)
        logging.info(f"Salvo: {filepath} ({len(df)} registros)")

    if falhas:
        logging.error(f"Falha em {len(falhas)} município(s): {', '.join(falhas)}. Rode a ingestão novamente.")
        sys.exit(1)
    logging.info(f"Ingestão concluída: {len(CIDADES)} municípios.")


if __name__ == "__main__":
    run_ingestion()
