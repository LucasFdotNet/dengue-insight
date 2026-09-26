import os
import joblib
import pandas as pd
from src.train import FEATURES, HORIZONTES, caminho_modelo, reconstruir_casos

def get_predictions(cidade, df_processed):
    # O modelo é único para todos os municípios; 'cidade' fica na assinatura por compatibilidade com o app
    df_valid = df_processed.dropna(subset=FEATURES)
    if df_valid.empty:
        return {}, ""

    last_row = df_valid.iloc[[-1]]
    ultima_data = pd.to_datetime(last_row['data_iniSE'].values[0])
    predictions = {}

    for horizon in HORIZONTES:
        model_path = caminho_modelo(horizon)
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            pred = reconstruir_casos(last_row, model.predict(last_row[FEATURES])).iloc[0]
            data_futura = ultima_data + pd.Timedelta(weeks=horizon)
            predictions[f'Semana +{horizon} ({data_futura.strftime("%d/%m/%Y")})'] = int(round(pred))

    return predictions, ultima_data.strftime("%d/%m/%Y")
