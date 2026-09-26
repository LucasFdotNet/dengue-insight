"""
Ingestão dos dados climáticos (reanálise ERA5 via Open-Meteo Historical API).

Para cada município de CIDADES, baixa a série diária desde 2010 pela latitude e
longitude da sede, agrega por semana epidemiológica (domingo a sábado, alinhada a
data_iniSE do InfoDengue) e salva em data/raw/clima/{cidade}_clima.csv.

Só entram semanas com os 7 dias disponíveis: o ERA5 chega com alguns dias de
atraso, e uma semana parcial teria média e chuva acumulada enviesadas.

Incremental: se o arquivo do município já existe, baixa só as últimas
SEMANAS_ATUALIZAR semanas (o ERA5 preliminar é substituído pelo definitivo em cerca
de 2 a 3 meses) e junta ao que já existe. Use --completo para baixar tudo de novo.

A Open-Meteo limita as chamadas por minuto, hora e dia, e uma série de 16 anos conta
como muitas chamadas. As esperas são automáticas (ver http_utils.py). Se o limite
diário for atingido, a ingestão para mantendo o que já foi salvo; basta rodar de novo
no dia seguinte para continuar de onde parou.
"""
import os
import sys
import logging
from datetime import date

import pandas as pd

from src.cidades import CIDADES
from src.http_utils import LimiteDiarioAtingido, get_com_retentativas

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
INICIO_SERIE = '2010-01-01'
SEMANAS_ATUALIZAR = 12


def fetch_clima_diario(lat, lon, inicio=INICIO_SERIE, fim=None):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": inicio,
        "end_date": fim or date.today().isoformat(),
        "daily": ",".join(VARIAVEIS_DIARIAS),
        "models": "era5",
        "timezone": "America/Sao_Paulo",
    }
    response = get_com_retentativas(URL, params, timeout=120, descricao=f"Open-Meteo ({lat}, {lon})")
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


def celula_era5(lat, lon):
    """Ponto da grade ERA5 (0,25°) mais próximo; municípios no mesmo ponto têm o mesmo clima."""
    return round(lat * 4) / 4, round(lon * 4) / 4


def run_ingestion_clima(completo=False):
    os.makedirs(PASTA_CLIMA, exist_ok=True)
    baixados = {}  # célula ERA5 -> (início pedido, dados diários), para não baixar o mesmo ponto duas vezes

    for cidade, info in CIDADES.items():
        filepath = f"{PASTA_CLIMA}/{cidade}_clima.csv"
        existente = None
        inicio = INICIO_SERIE
        if not completo and os.path.exists(filepath):
            existente = pd.read_csv(filepath, parse_dates=['data_iniSE'])
            # Recomeça num domingo, para as semanas refeitas ficarem completas
            inicio = (existente['data_iniSE'].max() - pd.Timedelta(weeks=SEMANAS_ATUALIZAR - 1)).date().isoformat()

        celula = celula_era5(info['lat'], info['lon'])
        if celula in baixados and baixados[celula][0] <= inicio:
            diario = baixados[celula][1]
            diario = diario[diario['time'] >= pd.Timestamp(inicio)]
            logging.info(f"Clima de {info['nome']}: mesmo ponto da grade ERA5 de um município já baixado.")
        else:
            logging.info(f"Buscando clima de {info['nome']} ({info['lat']}, {info['lon']}) desde {inicio}...")
            try:
                diario = fetch_clima_diario(info['lat'], info['lon'], inicio=inicio)
            except LimiteDiarioAtingido:
                logging.error("Limite diário da Open-Meteo atingido. O que já foi baixado está salvo; "
                              "rode este script novamente amanhã para continuar de onde parou.")
                sys.exit(1)
            baixados[celula] = (inicio, diario)

        df = agregar_semana_epidemiologica(diario)
        if existente is not None:
            df = pd.concat([existente[existente['data_iniSE'] < df['data_iniSE'].min()], df], ignore_index=True)
        df.to_csv(filepath, index=False, date_format='%Y-%m-%d')
        logging.info(f"Salvo: {filepath} ({len(df)} semanas, até {df['data_iniSE'].max():%d/%m/%Y})")

    logging.info(f"Ingestão de clima concluída: {len(CIDADES)} municípios.")


if __name__ == "__main__":
    run_ingestion_clima(completo='--completo' in sys.argv)
