"""
Previsões das próximas 4 semanas para um município, com os modelos de produção de train.py:
  - tendência (sobe, estável, cai): classificador com clima;
  - número de casos com intervalo de 80%: modelo por quantis.
Os dois modelos são independentes e podem divergir (por exemplo, tendência de subida com
aumento previsto de só 10% nos casos); o painel mostra os dois como são.
"""
import os

import joblib
import pandas as pd

from src.train import FEATURES, HORIZONTES, caminho_modelo


def modelos_disponiveis():
    return all(os.path.exists(caminho_modelo(tipo, h)) for tipo in ('classificador', 'quantis') for h in HORIZONTES)


def get_predictions(df_processed):
    """DataFrame com h, data, previsto, inferior, superior e tendencia, e a data da semana de partida.

    A semana de partida é a mais recente com as informações do modelo completas. Devolve um
    DataFrame vazio se os modelos não tiverem sido treinados.
    """
    df_valid = df_processed.dropna(subset=FEATURES)
    if df_valid.empty or not modelos_disponiveis():
        return pd.DataFrame(), None

    ultima = df_valid.iloc[[-1]]
    base = pd.Timestamp(ultima['data_iniSE'].values[0])
    linhas = []
    for h in HORIZONTES:
        casos = joblib.load(caminho_modelo('quantis', h)).prever(ultima, h).iloc[0]
        tendencia = joblib.load(caminho_modelo('classificador', h)).prever(ultima, h).iloc[0]
        linhas.append({
            'h': h,
            'data': base + pd.Timedelta(weeks=h),
            'previsto': int(round(casos['previsto'])),
            'inferior': int(round(casos['inferior'])),
            'superior': int(round(casos['superior'])),
            'tendencia': tendencia['tendencia'],
        })
    return pd.DataFrame(linhas), base
