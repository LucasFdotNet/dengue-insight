import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def gerar_analise_exploratoria(cidade, df):
    os.makedirs('reports/figures', exist_ok=True)
    
    cols = ['casos_est', 'tmin', 'tmin_lag_1', 'tmin_lag_2', 'rt', 'p_inc100k']
    cols_existentes = [c for c in cols if c in df.columns]
    
    # 1. Matriz de Correlacao
    plt.figure(figsize=(8, 6))
    sns.heatmap(df[cols_existentes].corr(), annot=True, cmap='coolwarm', fmt=".2f")
    plt.title(f'Matriz de Correlacao - {cidade.capitalize()}')
    plt.tight_layout()
    plt.savefig(f'reports/figures/{cidade}_correlacao.png')
    plt.close()
    
    # 2. Serie Temporal Casos x Temperatura Minima
    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax1.set_xlabel('Data')
    ax1.set_ylabel('Casos Estimados', color='tab:red')
    ax1.plot(df['data_iniSE'], df['casos_est'], color='tab:red')
    
    ax2 = ax1.twinx()
    ax2.set_ylabel('Temperatura Minima (°C)', color='tab:blue')
    ax2.plot(df['data_iniSE'], df['tmin'], color='tab:blue', alpha=0.6)
    
    plt.title(f'Casos Estimados vs Temperatura Minima - {cidade.capitalize()}')
    fig.tight_layout()
    plt.savefig(f'reports/figures/{cidade}_casos_vs_temp.png')
    plt.close()

def run_eda():
    processed_files = [f for f in os.listdir('data/processed') if f.endswith('_processed.csv')]
    for file in processed_files:
        cidade = file.split('_')[0]
        df = pd.read_csv(os.path.join('data/processed', file))
        df['data_iniSE'] = pd.to_datetime(df['data_iniSE'])
        gerar_analise_exploratoria(cidade, df)
        logging.info(f"EDA gerada para {cidade}.")

if __name__ == "__main__":
    run_eda()