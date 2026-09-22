import os
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_and_clean_data(filepath):
    df = pd.read_csv(filepath)
    
    # 1. Normalização de nomes das colunas
    rename_map = {
        'data_ini': 'data_iniSE',
        'temp_min': 'tmin',
        'temp_med': 'tmed',
        'temp_max': 'tmax',
        'inc': 'p_inc100k'
    }
    df = df.rename(columns=rename_map)
    
    # Garantir que a coluna tmin exista mesmo se ausente
    if 'tmin' not in df.columns:
        df['tmin'] = 22.0  # fallback neutro para temperatura
        
    # Converter data para datetime e ordenar
    data_col = 'data_iniSE' if 'data_iniSE' in df.columns else df.columns[0]
    df['data_iniSE'] = pd.to_datetime(df[data_col])
    df = df.sort_values('data_iniSE').reset_index(drop=True)
    
    # Preenchimento de nulos
    colunas_numericas = ['casos_est', 'tmin', 'rt', 'p_inc100k']
    for col in colunas_numericas:
        if col in df.columns:
            df[col] = df[col].interpolate().ffill().bfill()
            
    return df

def feature_engineering(df):
    df_feat = df.copy()
    
    # Criação de lags (1 a 4 semanas)
    for lag in range(1, 5):
        df_feat[f'casos_est_lag_{lag}'] = df_feat['casos_est'].shift(lag)
        df_feat[f'tmin_lag_{lag}'] = df_feat['tmin'].shift(lag)
        if 'rt' in df_feat.columns:
            df_feat[f'rt_lag_{lag}'] = df_feat['rt'].shift(lag)
        else:
            df_feat[f'rt_lag_{lag}'] = 1.0
        
    # Médias móveis
    df_feat['casos_est_roll_4'] = df_feat['casos_est'].rolling(window=4).mean()
    df_feat['tmin_roll_4'] = df_feat['tmin'].rolling(window=4).mean()
    
    # Targets futuros (1 a 4 semanas à frente)
    for horizon in range(1, 5):
        df_feat[f'target_h{horizon}'] = df_feat['casos_est'].shift(-horizon)
        
    return df_feat

def run_preprocessing():
    os.makedirs('data/processed', exist_ok=True)
    raw_files = [f for f in os.listdir('data/raw') if f.endswith('_raw.csv')]
    
    for file in raw_files:
        cidade = file.split('_')[0]
        logging.info(f"Processando {cidade}...")
        df = load_and_clean_data(os.path.join('data/raw', file))
        df_processed = feature_engineering(df)
        df_processed.to_csv(f"data/processed/{cidade}_processed.csv", index=False)
        logging.info(f"{cidade} processado com sucesso.")

if __name__ == "__main__":
    run_preprocessing()