import os
import pandas as pd
import logging
from src.cidades import CIDADES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

COLUNAS_OBRIGATORIAS = ['data_iniSE', 'casos_est', 'tmin', 'rt', 'p_inc100k']

def load_and_clean_data(filepath):
    df = pd.read_csv(filepath)
    
    # 1. Normalização de nomes das colunas (nomes devolvidos pela API do InfoDengue)
    rename_map = {
        'tempmin': 'tmin',
        'tempmed': 'tmed',
        'tempmax': 'tmax',
        'Rt': 'rt'
    }
    df = df.rename(columns=rename_map)
    
    # Falhar cedo: coluna ausente é erro, não recebe valor inventado
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError(f"{filepath}: colunas ausentes {faltando}")
        
    # Converter data para datetime e ordenar
    df['data_iniSE'] = pd.to_datetime(df['data_iniSE'])
    df = df.sort_values('data_iniSE').reset_index(drop=True)
    
    # Preenchimento de nulos apenas entre valores conhecidos (sem extrapolar nas pontas)
    for col in ['casos_est', 'tmin', 'rt', 'p_inc100k']:
        df[col] = df[col].interpolate(limit_area='inside')
            
    return df

def feature_engineering(df):
    df_feat = df.copy()
    
    # Criação de lags (1 a 4 semanas)
    for lag in range(1, 5):
        df_feat[f'casos_est_lag_{lag}'] = df_feat['casos_est'].shift(lag)
        df_feat[f'tmin_lag_{lag}'] = df_feat['tmin'].shift(lag)
        df_feat[f'rt_lag_{lag}'] = df_feat['rt'].shift(lag)
        
    # Médias móveis
    df_feat['casos_est_roll_4'] = df_feat['casos_est'].rolling(window=4).mean()
    df_feat['tmin_roll_4'] = df_feat['tmin'].rolling(window=4).mean()
    
    # Targets futuros (1 a 4 semanas à frente)
    for horizon in range(1, 5):
        df_feat[f'target_h{horizon}'] = df_feat['casos_est'].shift(-horizon)
        
    return df_feat

def run_preprocessing():
    os.makedirs('data/processed', exist_ok=True)
    
    for cidade in CIDADES:
        filepath = os.path.join('data/raw', f'{cidade}_raw.csv')
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{filepath} não encontrado. Execute a ingestão antes.")
        logging.info(f"Processando {cidade}...")
        df = load_and_clean_data(filepath)
        df_processed = feature_engineering(df)
        df_processed.to_csv(f"data/processed/{cidade}_processed.csv", index=False)
        logging.info(f"{cidade} processado com sucesso.")

if __name__ == "__main__":
    run_preprocessing()