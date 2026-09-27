"""
Previsões das próximas 4 semanas para um município, com os modelos de produção de train.py:
  - tendência (sobe, estável, cai): classificador com clima;
  - número de casos com intervalo de 80%: modelo por quantis.
Os dois modelos são independentes e podem divergir (por exemplo, tendência de subida com
aumento previsto de só 10% nos casos); o painel mostra os dois como são.

Semana de partida: nos municípios em que o InfoDengue publica o nowcast, é a semana mais
recente (os casos dela já são uma estimativa corrigida pelo atraso das notificações). Nos
municípios sem nowcast, as semanas mais recentes têm só os casos já notificados e estão
incompletas; a previsão parte da última semana considerada completa.
"""
import os

import joblib
import pandas as pd

from src.train import FEATURES, HORIZONTES, SEMANAS_INSTAVEIS, caminho_modelo

# Semanas finais incompletas nos municípios sem nowcast. Medido em 09/2026: em relação ao
# nível das semanas anteriores, a última semana tinha 23% dos casos, a penúltima 63% e a
# antepenúltima 76%, contra 84%, 82% e 87% nos municípios com nowcast (queda real de baixa
# temporada). A partir da 4ª semana mais recente, os dois grupos se aproximam.
SEMANAS_INCOMPLETAS_SEM_NOWCAST = 3


def modelos_disponiveis():
    return all(os.path.exists(caminho_modelo(tipo, h)) for tipo in ('classificador', 'quantis') for h in HORIZONTES)


def tem_nowcast(df_processed):
    """True se o InfoDengue publicou intervalo de nowcast em alguma das semanas recentes."""
    recentes = df_processed.dropna(subset=['casos_est']).tail(SEMANAS_INSTAVEIS)
    return bool(((recentes['casos_est_max'] - recentes['casos_est_min']) > 0).any())


def semanas_descartadas(df_processed):
    """Quantas semanas finais ficam fora do ponto de partida (0 se o município tem nowcast)."""
    return 0 if tem_nowcast(df_processed) else SEMANAS_INCOMPLETAS_SEM_NOWCAST


def get_predictions(df_processed):
    """(previsões, semana de partida, semanas descartadas).

    previsões: DataFrame com h, data, previsto, inferior, superior e tendencia; vazio se os
    modelos não tiverem sido treinados.
    """
    descartadas = semanas_descartadas(df_processed)
    df_valid = df_processed.dropna(subset=FEATURES)
    if descartadas:
        ultima_completa = df_processed.dropna(subset=['casos_est'])['data_iniSE'].iloc[-1 - descartadas]
        df_valid = df_valid[df_valid['data_iniSE'] <= ultima_completa]
    if df_valid.empty or not modelos_disponiveis():
        return pd.DataFrame(), None, descartadas

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
    return pd.DataFrame(linhas), base, descartadas
