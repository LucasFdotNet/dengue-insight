"""
Treino e avaliação do modelo único de previsão de casos (H+1 a H+4 semanas).

Um único LightGBM por horizonte, treinado com todos os municípios de treino juntos.
O alvo é relativo: log1p(casos daqui a H semanas) - log1p(casos atuais), ou seja,
o modelo prevê quanto os casos vão crescer ou cair, e não o número absoluto.
Isso deixa municípios de tamanhos diferentes na mesma escala e permite prever
valores acima dos já vistos no treino. Motivação e testes: "Decisões de Projeto"
no README.

Etapas:
  1. Avaliação walk-forward com retreino mensal: no início de cada mês, treina um
     modelo só com o que já era conhecido até ali e prevê as semanas daquele mês,
     nos municípios de treino e nos de validação espacial (que nunca entram em
     nenhum treino). Simula o uso real do modelo, retreinado todo mês. Sempre
     comparado ao baseline de persistência (casos daqui a H semanas = casos atuais).
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
    'semana_ano',                                        # sazonalidade
]
# Rt e clima ficam fora do modelo: não melhoraram a previsão (ver experimento_variaveis.py e o README)

# Tendência: "sobe" ou "cai" se a variação passa de 20% E de 5 casos; senão, "estável".
# O mínimo absoluto evita que oscilações pequenas (ex.: 2 -> 3 casos, +50%) contem como subida.
LIMIAR_TENDENCIA = 0.20
MIN_CASOS_TENDENCIA = 5
TENDENCIAS = ['sobe', 'estável', 'cai']

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


def classificar_tendencia(futuro, atual):
    """Classifica a variação de 'atual' para 'futuro' em 'sobe', 'estável' ou 'cai'."""
    futuro, atual = np.asarray(futuro, dtype=float), np.asarray(atual, dtype=float)
    variacao = futuro - atual
    limite = np.maximum(LIMIAR_TENDENCIA * atual, MIN_CASOS_TENDENCIA)
    return np.where(variacao > limite, 'sobe', np.where(-variacao > limite, 'cai', 'estável'))


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


def linhas_validas(df, horizonte, features=FEATURES):
    # Primeiro o dropna, depois o corte: assim também saem as semanas cujo alvo
    # (H semanas à frente) cai dentro das semanas instáveis
    validas = df.dropna(subset=features + [f'target_h{horizonte}'])
    return validas.groupby('cidade', sort=False).head(-SEMANAS_INSTAVEIS)


def avaliar_walk_forward(treino, validacao, horizontes=HORIZONTES, lacuna=0, features=FEATURES):
    """Erros semana a semana do modelo e do baseline, com retreino mensal.

    Cada linha usa os dados da semana t para prever a semana t + H. 'lacuna' simula
    dados atrasados: a previsão é feita na semana t + lacuna, quando as últimas
    'lacuna' semanas ainda não são confiáveis (usado em experimento_atraso.py).
    'features' permite testar outros conjuntos de variáveis (usado em experimento_variaveis.py).
    """
    ultima_semana = treino['data_iniSE'].max()
    meses = pd.period_range(f'{PRIMEIRO_ANO_TESTE}-01', ultima_semana, freq='M')
    atraso = pd.Timedelta(weeks=lacuna)
    erros = []
    for horizonte in horizontes:
        passo = pd.Timedelta(weeks=horizonte)
        dados_treino = linhas_validas(treino, horizonte, features)
        dados_teste = [(grupo, linhas_validas(dados, horizonte, features)) for grupo, dados in
                       [('treino', treino), ('validacao', validacao)]]
        for mes in meses:
            inicio, fim = mes.start_time, (mes + 1).start_time
            # Retreino no início do mês: só entram semanas cujo alvo já era conhecido (e confiável) antes dele
            tr = dados_treino[dados_treino['data_iniSE'] + passo < inicio - atraso]
            modelo = novo_modelo().fit(tr[features], alvo_relativo(tr, horizonte))

            for grupo, dados in dados_teste:
                # Semanas em que a previsão seria feita dentro deste mês
                momento = dados['data_iniSE'] + atraso
                te = dados[(momento >= inicio) & (momento < fim)]
                if te.empty:
                    continue
                real = te[f'target_h{horizonte}']
                previsto = reconstruir_casos(te, modelo.predict(te[features]))
                erros.append(pd.DataFrame({
                    'Grupo': grupo,
                    'Cidade': te['cidade'].map(lambda k: CIDADES[k]['nome']),
                    'Ano': (te['data_iniSE'] + passo).dt.year,
                    'Horizonte': f'Semana +{horizonte}',
                    'cidade': te['cidade'],
                    'h': horizonte,
                    'data_alvo': te['data_iniSE'] + passo,
                    'previsto': previsto,
                    'real': real,
                    'erro_lgbm': real - previsto,
                    'erro_baseline': real - te['casos_est'],  # persistência: repete os casos da semana t
                    'atual': te['casos_est'],
                    'anterior': te['casos_est_lag_1'],
                }))
        logging.info(f"Walk-forward H+{horizonte} concluído ({len(meses)} retreinos mensais).")
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
    resumo = erros.groupby(por, sort=False).apply(metricas, include_groups=False).reset_index()
    return resumo.astype({'Semanas': int})


def resumir_tendencia(erros):
    """Acerto da tendência (sobe / estável / cai) do modelo e de duas referências simples."""
    real = classificar_tendencia(erros['real'], erros['atual'])
    modelo = classificar_tendencia(erros['previsto'], erros['atual'])
    # Referência: estender por H semanas a variação da última semana
    variacao_semanal = erros['atual'] / erros['anterior'].where(erros['anterior'] > 0)
    extrapolado = (erros['atual'] * variacao_semanal ** erros['h']).fillna(erros['atual'])
    ultima_semana = classificar_tendencia(extrapolado, erros['atual'])
    df = erros[['Grupo', 'Horizonte']].assign(real=real, modelo=modelo, ultima_semana=ultima_semana)

    def metricas(g):
        subiu, previu_subida, caiu = g['real'] == 'sobe', g['modelo'] == 'sobe', g['real'] == 'cai'
        oposto = ((g['real'] == 'sobe') & (g['modelo'] == 'cai')) | ((g['real'] == 'cai') & (g['modelo'] == 'sobe'))
        return pd.Series({
            'Semanas': len(g),
            'Acerto_modelo': round((g['real'] == g['modelo']).mean(), 3),
            'Acerto_sempre_estavel': round((g['real'] == 'estável').mean(), 3),
            'Acerto_tendencia_ultima_semana': round((g['real'] == g['ultima_semana']).mean(), 3),
            'Subidas_detectadas': round((g.loc[subiu, 'modelo'] == 'sobe').mean(), 3),
            'Alarmes_subida_corretos': round((g.loc[previu_subida, 'real'] == 'sobe').mean(), 3),
            'Quedas_detectadas': round((g.loc[caiu, 'modelo'] == 'cai').mean(), 3),
            'Sentido_oposto': round(oposto.mean(), 3),
        })
    resumo = df.groupby(['Grupo', 'Horizonte'], sort=False).apply(metricas, include_groups=False).reset_index()
    return resumo.astype({'Semanas': int})


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
    resumir_tendencia(erros).to_csv('reports/metricas_tendencia.csv', index=False)
    logging.info("Métricas salvas em reports/metricas_modelos.csv, metricas_por_ano.csv, metricas_gerais.csv "
                 "e metricas_tendencia.csv.")

    # Previsões fora da amostra (cada semana prevista por um modelo que não a viu no treino),
    # usadas pelo app para mostrar como o modelo teria se saído no passado
    previsoes = erros[['cidade', 'h', 'data_alvo', 'real', 'previsto']].copy()
    previsoes['previsto'] = previsoes['previsto'].round(1)
    previsoes.sort_values(['cidade', 'h', 'data_alvo']).to_csv(ARQUIVO_PREVISOES_PASSADAS, index=False)
    logging.info(f"Previsões do walk-forward salvas em {ARQUIVO_PREVISOES_PASSADAS}.")

    treinar_producao(treino)


if __name__ == "__main__":
    run_training()
