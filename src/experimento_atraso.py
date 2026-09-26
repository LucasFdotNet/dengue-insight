"""
Experimento: o modelo ainda seria útil com dados atrasados?

Em tempo real, os casos das semanas mais recentes ainda estão incompletos, porque as
notificações chegam com atraso. A validação walk-forward do train.py usa os dados já
revisados, então é otimista nesse ponto.

Este experimento simula o pior caso: na semana X, as semanas X, X-1, ..., X-(LACUNA-1)
são consideradas não confiáveis e não podem ser usadas. O último dado disponível é o
da semana X-LACUNA. Para prever X+N (antecedência de N semanas), o modelo precisa
então prever N+LACUNA semanas à frente a partir de X-LACUNA. O baseline, da mesma
forma, repete o último valor confiável (X-LACUNA).

É uma simulação conservadora: na prática o InfoDengue fornece uma estimativa (nowcast)
para as semanas recentes, que é incerta mas não inexistente.

Compara, com a mesma validação walk-forward com retreino mensal do train.py:
  - sem lacuna (cenário regular, igual ao train.py);
  - lacuna de 4 semanas (último dado confiável: X-4);
  - lacuna de 5 semanas (último dado confiável: X-5).
Para uma comparação justa, cada antecedência é avaliada nas mesmas semanas-alvo em
todos os cenários.

Saída: reports/experimento_atraso.csv
"""
import logging

import pandas as pd

from src.train import HORIZONTES, avaliar_walk_forward, carregar

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LACUNAS = [0, 4, 5]
ARQUIVO_SAIDA = 'reports/experimento_atraso.csv'


def adicionar_alvos(df, horizonte_maximo):
    """Cria target_h{H} para horizontes além dos calculados no pré-processamento."""
    df = df.sort_values(['cidade', 'data_iniSE']).copy()
    for h in range(1, horizonte_maximo + 1):
        df[f'target_h{h}'] = df.groupby('cidade')['casos_est'].shift(-h)
    return df


def run_experimento():
    horizonte_maximo = max(HORIZONTES) + max(LACUNAS)
    treino = adicionar_alvos(carregar('treino'), horizonte_maximo)
    validacao = adicionar_alvos(carregar('validacao'), horizonte_maximo)

    resultados = []
    for lacuna in LACUNAS:
        logging.info(f"Cenário com lacuna de {lacuna} semana(s)...")
        erros = avaliar_walk_forward(treino, validacao,
                                     horizontes=[n + lacuna for n in HORIZONTES], lacuna=lacuna)
        erros['Lacuna'] = lacuna
        erros['Antecedencia'] = erros['h'] - lacuna
        resultados.append(erros)
    erros = pd.concat(resultados, ignore_index=True)

    # Mesmas semanas-alvo em todos os cenários, para cada município e antecedência
    chave = ['cidade', 'Antecedencia', 'data_alvo']
    comuns = erros.groupby(chave)['Lacuna'].nunique()
    comuns = comuns[comuns == len(LACUNAS)].reset_index()[chave]
    erros = erros.merge(comuns, on=chave)

    resumo = (erros.groupby(['Grupo', 'Antecedencia', 'Lacuna'])
              .agg(Semanas=('real', 'size'),
                   Baseline_MAE=('erro_baseline', lambda e: e.abs().mean()),
                   LGBM_MAE=('erro_lgbm', lambda e: e.abs().mean()))
              .reset_index())
    resumo['Razao_MAE'] = resumo['LGBM_MAE'] / resumo['Baseline_MAE']
    # Quanto o erro do modelo cresce em relação ao cenário sem lacuna
    sem_lacuna = resumo[resumo['Lacuna'] == 0].set_index(['Grupo', 'Antecedencia'])['LGBM_MAE']
    resumo['LGBM_MAE_vs_sem_lacuna'] = resumo['LGBM_MAE'] / resumo.set_index(['Grupo', 'Antecedencia']).index.map(sem_lacuna)
    resumo = resumo.round({'Baseline_MAE': 2, 'LGBM_MAE': 2, 'Razao_MAE': 3, 'LGBM_MAE_vs_sem_lacuna': 3})
    resumo.to_csv(ARQUIVO_SAIDA, index=False)
    logging.info(f"Resultado salvo em {ARQUIVO_SAIDA}.")
    print(resumo.to_string(index=False))


if __name__ == "__main__":
    run_experimento()
