import os
import requests
import pandas as pd
import logging
from datetime import date
from io import StringIO
from src.cidades import CIDADES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')




def fetch_infodengue_data(geocode, ey_start=2010, ey_end=None):
    url = "https://info.dengue.mat.br/api/alertcity"
    params = {
        "geocode": geocode,
        "disease": "dengue",
        "format": "csv",
        "ew_start": 1,
        "ew_end": 53,
        "ey_start": ey_start,
        "ey_end": ey_end or date.today().year
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return pd.read_csv(StringIO(response.text))
    except Exception as e:
        logging.error(f"Erro ao buscar dados para o geocode {geocode}: {e}")
        return None

def run_ingestion():
    os.makedirs('data/raw', exist_ok=True)

    for cidade, info in CIDADES.items():
        logging.info(f"Buscando dados de {info['nome']} ({info['geocode']})...")
        df = fetch_infodengue_data(info["geocode"])
        if df is not None and not df.empty:
            filepath = f"data/raw/{cidade}_raw.csv"
            df.to_csv(filepath, index=False)
            logging.info(f"Salvo: {filepath} ({len(df)} registros)")
        else:
            logging.warning(f"Sem dados retornados para {cidade}.")

if __name__ == "__main__":
    run_ingestion()