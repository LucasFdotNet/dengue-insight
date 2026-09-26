import os
import pandas as pd
import logging
from src.cidades import CIDADES

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

COLUNAS_OBRIGATORIAS = ['data_iniSE', 'casos_est', 'rt', 'p_inc100k']
COLUNAS_CLIMA = ['tmin', 'tmed', 'tmax', 'precipitacao', 'umidade']
# Clima do InfoDengue, substituído pelo ERA5 (ver Decisões de Projeto no README)
COLUNAS_CLIMA_INFODENGUE = ['tempmin', 'tempmed', 'tempmax', 'umidmin', 'umidmed', 'umidmax']

def _verificar_colunas(df, obrigatorias, filepath):
    # Falhar cedo: coluna ausente é erro, não recebe valor inventado
    faltando = [c for c in obrigatorias if c not in df.columns]
    if faltando:
        raise ValueError(f"{filepath}: colunas ausentes {faltando}")

def load_and_clean_data(filepath, clima_path):
    df = pd.read_csv(filepath)
    
    # 1. Normalização de nomes das colunas (nomes devolvidos pela API do InfoDengue)
    df = df.rename(columns={'Rt': 'rt'}).drop(columns=COLUNAS_CLIMA_INFODENGUE, errors='ignore')
    _verificar_colunas(df, COLUNAS_OBRIGATORIAS, filepath)
        
    # Converter data para datetime e ordenar
    df['data_iniSE'] = pd.to_datetime(df['data_iniSE'])
    df = df.sort_values('data_iniSE').reset_index(drop=True)
    
    # 2. Clima semanal (ERA5). Left join: semanas recentes que o ERA5 ainda
    # não cobre ficam sem clima, em vez de receber valor copiado.
    clima = pd.read_csv(clima_path, parse_dates=['data_iniSE'])
    _verificar_colunas(clima, ['data_iniSE'] + COLUNAS_CLIMA, clima_path)
    df = df.merge(clima[['data_iniSE'] + COLUNAS_CLIMA], on='data_iniSE', how='left', validate='one_to_one')
    
    # Preenchimento de nulos apenas entre valores conhecidos (sem extrapolar nas pontas)
    for col in ['casos_est', 'rt', 'p_inc100k'] + COLUNAS_CLIMA:
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
        clima_path = os.path.join('data/raw/clima', f'{cidade}_clima.csv')
        for path, script in [(filepath, 'ingestion.py'), (clima_path, 'ingestion_clima.py')]:
            if not os.path.exists(path):
                raise FileNotFoundError(f"{path} não encontrado. Execute {script} antes.")
        logging.info(f"Processando {cidade}...")
        df = load_and_clean_data(filepath, clima_path)
        df_processed = feature_engineering(df)
        df_processed.to_csv(f"data/processed/{cidade}_processed.csv", index=False)
        logging.info(f"{cidade} processado com sucesso.")

if __name__ == "__main__":
    run_preprocessing()