import os
import joblib
import pandas as pd
from src.train import FEATURES

def get_predictions(cidade, df_processed):
    df_valid = df_processed.dropna(subset=FEATURES)
    if df_valid.empty:
        return {}, ""
        
    last_row = df_valid.iloc[[-1]]
    ultima_data = pd.to_datetime(last_row['data_iniSE'].values[0])
    predictions = {}
    
    for horizon in range(1, 5):
        model_path = f"models/trained_models/{cidade}_model_h{horizon}.joblib"
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            pred = model.predict(last_row[FEATURES])[0]
            data_futura = ultima_data + pd.Timedelta(weeks=horizon)
            predictions[f'Semana +{horizon} ({data_futura.strftime("%d/%m/%Y")})'] = max(0, int(round(pred)))
            
    return predictions, ultima_data.strftime("%d/%m/%Y")