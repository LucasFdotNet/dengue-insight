import os
import joblib
import pandas as pd
import numpy as np
import logging
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SEMANAS_INSTAVEIS = 8  # semanas finais cujo casos_est (nowcast) ainda é revisado

FEATURES = [
    'casos_est_lag_1', 'casos_est_lag_2', 'casos_est_lag_3', 'casos_est_lag_4',
    'casos_est_roll_4', 'tmin_lag_1', 'tmin_roll_4', 'rt_lag_1', 'p_inc100k'
]

def train_and_evaluate_city(cidade, df):
    os.makedirs('models/trained_models', exist_ok=True)
    os.makedirs('reports', exist_ok=True)
    
    metricas = []
    
    for horizon in range(1, 5):
        target = f'target_h{horizon}'
        df_valid = df.dropna(subset=FEATURES + [target]).iloc[:-SEMANAS_INSTAVEIS].copy()        

        # Divisão cronológica: 80% treino, 20% teste
        split_idx = int(len(df_valid) * 0.8)
        train_data = df_valid.iloc[:split_idx]
        test_data = df_valid.iloc[split_idx:]
        
        X_train, y_train = train_data[FEATURES], train_data[target]
        X_test, y_test = test_data[FEATURES], test_data[target]
        
        # 1. Modelo Baseline (Persistência temporal: assume que os casos futuros repetem os atuais)
        preds_baseline = test_data['casos_est'].values
        mae_base = mean_absolute_error(y_test, preds_baseline)
        rmse_base = np.sqrt(mean_squared_error(y_test, preds_baseline))
        r2_base = r2_score(y_test, preds_baseline)
        
        # 2. Modelo de Machine Learning (LightGBM)
        model = LGBMRegressor(n_estimators=100, learning_rate=0.05, random_state=42, verbose=-1)
        model.fit(X_train, y_train)
        
        preds_lgbm = model.predict(X_test)
        mae_lgbm = mean_absolute_error(y_test, preds_lgbm)
        rmse_lgbm = np.sqrt(mean_squared_error(y_test, preds_lgbm))
        r2_lgbm = r2_score(y_test, preds_lgbm)
        
        # Registro comparativo
        metricas.append({
            'Cidade': cidade.capitalize(),
            'Horizonte': f'Semana +{horizon}',
            'Baseline_MAE': round(mae_base, 2),
            'LGBM_MAE': round(mae_lgbm, 2),
            'Baseline_RMSE': round(rmse_base, 2),
            'LGBM_RMSE': round(rmse_lgbm, 2),
            'Baseline_R2': round(r2_base, 4),
            'LGBM_R2': round(r2_lgbm, 4)
        })
        
        logging.info(f"[{cidade.capitalize()} | H+{horizon}] Baseline MAE: {mae_base:.2f} vs LGBM MAE: {mae_lgbm:.2f}")
        joblib.dump(model, f"models/trained_models/{cidade}_model_h{horizon}.joblib")
        
    return pd.DataFrame(metricas)

def run_training():
    processed_files = [f for f in os.listdir('data/processed') if f.endswith('_processed.csv')]
    all_metrics = []
    
    for file in processed_files:
        cidade = file.removesuffix('_processed.csv')
        df = pd.read_csv(os.path.join('data/processed', file))
        logging.info(f"Treinando modelos para {cidade}...")
        df_metricas = train_and_evaluate_city(cidade, df)
        all_metrics.append(df_metricas)
        
    if all_metrics:
        tabela_consolidada = pd.concat(all_metrics, ignore_index=True)
        tabela_consolidada.to_csv("reports/metricas_modelos.csv", index=False)
        logging.info("Tabela consolidada salva com sucesso em 'reports/metricas_modelos.csv'.")

if __name__ == "__main__":
    run_training()