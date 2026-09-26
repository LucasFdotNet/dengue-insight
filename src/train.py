"""
Treino e avaliação do modelo único de previsão de casos (H+1 a H+4 semanas).

Um único LightGBM por horizonte, treinado com todos os municípios de treino juntos.
O alvo é relativo: log1p(casos daqui a H semanas) - log1p(casos atuais), ou seja,
o modelo prevê quanto os casos vão crescer ou cair, e não o número absoluto.
Isso deixa municípios de tamanhos diferentes na mesma escala e permite prever
valores acima dos já vistos no treino. Motivação e testes: "Decisões de Projeto"
no README.

Etapas:
  1. Avaliação walk-forward anual: para cada ano de teste, treina só com semanas
     anteriores a ele e testa no ano inteiro, nos municípios de treino e nos de
     validação espacial (que nunca entram em nenhum treino). Sempre comparado ao
     baseline de persistência (casos daqui a H semanas = casos atuais).
  2. Modelo de produção: treinado com toda a série dos municípios de treino e
     salvo para o predict.py e o app.
"""
import os
import joblib
import pandas as pd
import numpy as np
import logging
from lightgbm import LGBMRegressor
from src.cidades import CIDADES, cidades_por_papel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Semanas finais cujo casos_est ainda é revisado pelo InfoDengue (nowcast).
# Valor = maior número de semanas finais em nowcast entre as cidades de treino,
# observado em 09/2026 em Cosmópolis e Indaiatuba (10 semanas). Ver README.
SEMANAS_INSTAVEIS = 10

HORIZONTES = range(1, 5)
PRIMEIRO_ANO_TESTE = 2015  # garante ao menos 5 anos de histórico (2010-2014) no primeiro treino

FEATURES = [
    'log_casos',                                        # nível atual (escala log)
    'var_log_1', 'var_log_2', 'var_log_3', 'var_log_4',  # crescimento em relação a 1-4 semanas atrás
    'rt_lag_1',                                          # taxa de reprodução da semana anterior
    'semana_ano',                                        # sazonalidade
]

PASTA_MODELOS = 'models/trained_models'
ARQUIVO_PREVISOES_PASSADAS = 'reports/previsoes_walkforward.csv'


def caminho_modelo(horizonte):
    return f"{PASTA_MODELOS}/modelo_unico_h{horizonte}.joblib"


def novo_modelo():
    return LGBMRegressor(n_estimators=300, learning_rate=0.05, random_state=42, verbose=-1)


def alvo_relativo(df, horizonte):
    return np.log1p(df[f'target_h{horizonte}']) - df['log_casos']


def reconstruir_casos(df, previsao_relativa):
    """Converte a previsão relativa de volta para número de casos (nunca negativo)."""
    return np.maximum(np.expm1(df['log_casos'] + previsao_relativa), 0)


def carregar(papel):
    partes = []
    for cidade in cidades_por_papel(papel):
        filepath = os.path.join('data/processed', f'{cidade}_processed.csv')
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{filepath} não encontrado. Execute preprocessing.py antes.")
        df = pd.read_csv(filepath, parse_dates=['data_iniSE'])
        df['cidade'] = cidade
        partes.append(df)
    return pd.concat(partes, ignore_index=True)


def linhas_validas(df, horizonte):
    # Primeiro o dropna, depois o corte: assim também saem as semanas cujo alvo
    # (H semanas à frente) cai dentro das semanas instáveis
    validas = df.dropna(subset=FEATURES + [f'target_h{horizonte}'])
    return validas.groupby('cidade', sort=False).head(-SEMANAS_INSTAVEIS)


def avaliar_walk_forward(treino, validacao):
    """Erros absolutos semana a semana do modelo e do baseline, por ano de teste."""
    ultimo_ano = treino['data_iniSE'].dt.year.max()
    erros = []
    for horizonte in HORIZONTES:
        dados_treino = linhas_validas(treino, horizonte)
        for ano in range(PRIMEIRO_ANO_TESTE, ultimo_ano + 1):
            inicio, fim = pd.Timestamp(f'{ano}-01-01'), pd.Timestamp(f'{ano + 1}-01-01')
            # O alvo de cada semana de treino (H semanas à frente) precisa estar antes do ano de teste
            tr = dados_treino[dados_treino['data_iniSE'] + pd.Timedelta(weeks=horizonte) < inicio]
            modelo = novo_modelo().fit(tr[FEATURES], alvo_relativo(tr, horizonte))

            for grupo, dados in [('treino', treino), ('validacao', validacao)]:
                te = linhas_validas(dados, horizonte)
                te = te[(te['data_iniSE'] >= inicio) & (te['data_iniSE'] < fim)]
                if te.empty:
                    continue
                real = te[f'target_h{horizonte}']
                previsto = reconstruir_casos(te, modelo.predict(te[FEATURES]))
                erros.append(pd.DataFrame({
                    'Grupo': grupo,
                    'Cidade': te['cidade'].map(lambda k: CIDADES[k]['nome']),
                    'Ano': ano,
                    'Horizonte': f'Semana +{horizonte}',
                    'cidade': te['cidade'],
                    'h': horizonte,
                    'data_alvo': te['data_iniSE'] + pd.Timedelta(weeks=horizonte),
                    'previsto': previsto,
                    'real': real,
                    'erro_lgbm': real - previsto,
                    'erro_baseline': real - te['casos_est'],  # persistência: repete os casos atuais
                }))
        logging.info(f"Walk-forward H+{horizonte} concluído.")
    return pd.concat(erros, ignore_index=True)


def resumir(erros, por):
    def metricas(g):
        mae_b, mae_m = g['erro_baseline'].abs().mean(), g['erro_lgbm'].abs().mean()
        variancia = ((g['real'] - g['real'].mean()) ** 2).sum()
        return pd.Series({
            'Semanas': len(g),
            'Baseline_MAE': round(mae_b, 2),
            'LGBM_MAE': round(mae_m, 2),
            'Baseline_RMSE': round(np.sqrt((g['erro_baseline'] ** 2).mean()), 2),
            'LGBM_RMSE': round(np.sqrt((g['erro_lgbm'] ** 2).mean()), 2),
            'Baseline_R2': round(1 - (g['erro_baseline'] ** 2).sum() / variancia, 4),
            'LGBM_R2': round(1 - (g['erro_lgbm'] ** 2).sum() / variancia, 4),
            # < 1: o modelo erra menos que o baseline
            'Razao_MAE': round(mae_m / mae_b, 3),
        })
    return erros.groupby(por, sort=False).apply(metricas, include_groups=False).reset_index()


def treinar_producao(treino):
    os.makedirs(PASTA_MODELOS, exist_ok=True)
    for horizonte in HORIZONTES:
        tr = linhas_validas(treino, horizonte)
        modelo = novo_modelo().fit(tr[FEATURES], alvo_relativo(tr, horizonte))
        joblib.dump(modelo, caminho_modelo(horizonte))
        logging.info(f"Modelo de produção H+{horizonte} salvo ({len(tr)} semanas, até {tr['data_iniSE'].max():%d/%m/%Y}).")


def run_training():
    os.makedirs('reports', exist_ok=True)
    treino, validacao = carregar('treino'), carregar('validacao')

    erros = avaliar_walk_forward(treino, validacao)
    resumir(erros, ['Grupo', 'Cidade', 'Horizonte']).to_csv('reports/metricas_modelos.csv', index=False)
    resumir(erros, ['Grupo', 'Ano', 'Horizonte']).to_csv('reports/metricas_por_ano.csv', index=False)
    geral = resumir(erros, ['Grupo', 'Horizonte'])
    geral.to_csv('reports/metricas_gerais.csv', index=False)
    for _, linha in geral.iterrows():
        logging.info(f"[{linha['Grupo']} | {linha['Horizonte']}] Baseline MAE: {linha['Baseline_MAE']:.2f} "
                     f"vs LGBM MAE: {linha['LGBM_MAE']:.2f} (razão {linha['Razao_MAE']:.2f})")
    logging.info("Métricas salvas em reports/metricas_modelos.csv, metricas_por_ano.csv e metricas_gerais.csv.")

    # Previsões fora da amostra (cada semana prevista por um modelo que não a viu no treino),
    # usadas pelo app para mostrar como o modelo teria se saído no passado
    previsoes = erros[['cidade', 'h', 'data_alvo', 'real', 'previsto']].copy()
    previsoes['previsto'] = previsoes['previsto'].round(1)
    previsoes.sort_values(['cidade', 'h', 'data_alvo']).to_csv(ARQUIVO_PREVISOES_PASSADAS, index=False)
    logging.info(f"Previsões do walk-forward salvas em {ARQUIVO_PREVISOES_PASSADAS}.")

    treinar_producao(treino)


if __name__ == "__main__":
    run_training()
