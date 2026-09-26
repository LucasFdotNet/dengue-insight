"""
Ingestão dos dados climáticos (reanálise ERA5 via Open-Meteo Historical API).

Para cada município de CIDADES, baixa a série diária desde 2010 pela latitude e
longitude da sede, agrega por semana epidemiológica (domingo a sábado, alinhada a
data_iniSE do InfoDengue) e salva em data/raw/clima/{cidade}_clima.csv.

Só entram semanas com os 7 dias disponíveis: o ERA5 chega com alguns dias de
atraso, e uma semana parcial teria média e chuva acumulada enviesadas.
"""
import os
import time
import logging
from datetime import date

import pandas as pd
import requests

from src.cidades import CIDADES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

URL = "https://archive-api.open-meteo.com/v1/archive"
VARIAVEIS_DIARIAS = {
    'temperature_2m_min': 'tmin',
    'temperature_2m_mean': 'tmed',
    'temperature_2m_max': 'tmax',
    'precipitation_sum': 'precipitacao',
    'relative_humidity_2m_mean': 'umidade',
}
PASTA_CLIMA = 'data/raw/clima'
# A Open-Meteo conta uma série longa como várias chamadas no limite por minuto;
# ao receber 429, espera a janela do limite passar e tenta de novo.
TENTATIVAS = 5
ESPERA_429 = 65  # segundos


def fetch_clima_diario(lat, lon, inicio='2010-01-01', fim=None):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": inicio,
        "end_date": fim or date.today().isoformat(),
        "daily": ",".join(VARIAVEIS_DIARIAS),
        "models": "era5",
        "timezone": "America/Sao_Paulo",
    }
    for tentativa in range(1, TENTATIVAS + 1):
        response = requests.get(URL, params=params, timeout=120)
        if response.status_code != 429 or tentativa == TENTATIVAS:
            break
        logging.warning(f"Limite de requisições da Open-Meteo; nova tentativa em {ESPERA_429}s ({tentativa}/{TENTATIVAS - 1})...")
        time.sleep(ESPERA_429)
    response.raise_for_status()
    df = pd.DataFrame(response.json()["daily"]).rename(columns=VARIAVEIS_DIARIAS)
    df['time'] = pd.to_datetime(df['time'])
    return df.dropna()


def agregar_semana_epidemiologica(df_diario):
    df = df_diario.copy()
    # Semana epidemiológica começa no domingo (dayofweek: segunda=0 ... domingo=6)
    df['data_iniSE'] = df['time'] - pd.to_timedelta((df['time'].dt.dayofweek + 1) % 7, unit='D')
    semanal = df.groupby('data_iniSE').agg(
        tmin=('tmin', 'mean'),
        tmed=('tmed', 'mean'),
        tmax=('tmax', 'mean'),
        precipitacao=('precipitacao', 'sum'),
        umidade=('umidade', 'mean'),
        dias=('time', 'size'),
    )
    semanal = semanal[semanal['dias'] == 7].drop(columns='dias')
    return semanal.round(2).reset_index()


def run_ingestion_clima():
    os.makedirs(PASTA_CLIMA, exist_ok=True)

    for cidade, info in CIDADES.items():
        logging.info(f"Buscando clima de {info['nome']} ({info['lat']}, {info['lon']})...")
        try:
            df = agregar_semana_epidemiologica(fetch_clima_diario(info['lat'], info['lon']))
        except Exception as e:
            logging.error(f"Erro ao buscar clima de {cidade}: {e}")
            continue
        filepath = f"{PASTA_CLIMA}/{cidade}_clima.csv"
        df.to_csv(filepath, index=False)
        logging.info(f"Salvo: {filepath} ({len(df)} semanas, até {df['data_iniSE'].max():%d/%m/%Y})")


if __name__ == "__main__":
    run_ingestion_clima()
