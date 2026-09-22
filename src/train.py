import os
import joblib
import pandas as pd
import logging
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

FEATURES = [
    'casos_est_lag_1', 'casos_est_lag_2', 'casos_est_lag_3', 'casos_est_lag_4',
    'casos_est_roll_4', 'tmin_lag_1', 'tmin_roll_4', 'rt_lag_1', 'p_inc100k'
]

def train_model_for_city(cidade, df):
    os.makedirs('models/trained_models', exist_ok=True)
    for horizon in range(1, 5):
        target = f'target_h{horizon}'
        df_train_valid = df.dropna(subset=FEATURES + [target]).copy()
        
        split_idx = int(len(df_train_valid) * 0.8)
        train_data = df_train_valid.iloc[:split_idx]
        test_data = df_train_valid.iloc[split_idx:]
        
        X_train, y_train = train_data[FEATURES], train_data[target]
        X_test, y_test = test_data[FEATURES], test_data[target]
        
        model = LGBMRegressor(n_estimators=100, learning_rate=0.05, random_state=42, verbose=-1)
        model.fit(X_train, y_train)
        
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        rmse = mean_squared_error(y_test, preds)**0.5
        r2 = r2_score(y_test, preds)
        
        logging.info(f"[{cidade.capitalize()} | H+{horizon}] MAE: {mae:.2f} | RMSE: {rmse:.2f} | R2: {r2:.2f}")
        joblib.dump(model, f"models/trained_models/{cidade}_model_h{horizon}.joblib")

def run_training():
    processed_files = [f for f in os.listdir('data/processed') if f.endswith('_processed.csv')]
    for file in processed_files:
        cidade = file.split('_')[0]
        df = pd.read_csv(os.path.join('data/processed', file))
        logging.info(f"Treinando modelos para {cidade}...")
        train_model_for_city(cidade, df)

if __name__ == "__main__":
    run_training()