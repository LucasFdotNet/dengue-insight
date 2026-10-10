"""
Estados de incidência (normal ou alto) e episódios de nível alto.

O gestor decide pelo nível em que os casos vão estar: mobiliza recursos quando o município
entra no nível alto, mantém enquanto continua alto e desmobiliza quando volta ao normal.
Este módulo define esses estados com limiares próprios de cada município, calculados só
com os dados do próprio projeto (nenhum indicador calculado pelo InfoDengue é usado).

Limiar (por município e ano): percentil PERCENTIL_ALTO dos casos semanais dos anos
anteriores, com mínimo de MIN_CASOS_ALTO casos. Antes do primeiro ano avaliado
(PRIMEIRO_ANO_TESTE), usa os anos de 2010 até o ano anterior a ele, para os anos iniciais
não ficarem com pouco histórico; isso só afeta o rótulo das semanas de treino anteriores a
2015, nunca as avaliadas. Como o limiar é um percentil dos casos do próprio município, a
população não entra na conta.

  - alto: casos estimados da semana >= limiar do ano da semana;
  - alto_h<H>: estado da semana S+H (alvo dos modelos de estado);
  - razao_limiar: log(1 + casos) - log(1 + limiar), a distância da semana atual ao limiar
    (positiva no nível alto), comparável entre municípios.

Episódio: semanas altas seguidas, juntando interrupções de até MAX_INTERRUPCAO semanas, com
pelo menos MIN_SEMANAS_EPISODIO semanas. Episódios mais curtos são oscilações em torno do
limiar, que não justificam mobilizar uma equipe.

Comparação (só para validar a definição, fora dos modelos): com o percentil 90%, 88% das
semanas altas estão no nível epidêmico do InfoDengue (nivel_inc = 2), cujos limiares vêm
do método MEM aplicado ao histórico de cada município.
"""
import numpy as np
import pandas as pd

from src.train import HORIZONTES, PRIMEIRO_ANO_TESTE

PERCENTIL_ALTO = 0.90
PERCENTIL_SENSIBILIDADE = 0.80
MIN_CASOS_ALTO = 10
MIN_SEMANAS_EPISODIO = 2
MAX_INTERRUPCAO = 1


def limiares(df, percentil=PERCENTIL_ALTO):
    """Limiar de cada município e ano (DataFrame com cidade, ano, limiar)."""
    linhas = []
    for cidade, g in df.groupby('cidade'):
        anos = g['data_iniSE'].dt.year
        for ano in sorted(anos.unique()):
            ate = max(ano, PRIMEIRO_ANO_TESTE)
            passado = g.loc[anos < ate, 'casos_est'].dropna()
            limiar = max(passado.quantile(percentil), MIN_CASOS_ALTO) if len(passado) else np.nan
            linhas.append({'cidade': cidade, 'ano': ano, 'limiar': limiar})
    return pd.DataFrame(linhas)


def adicionar_estados(df, percentil=PERCENTIL_ALTO):
    """Acrescenta limiar, alto, razao_limiar e alto_h1 a alto_h4 (NaN onde o futuro não existe)."""
    df = df.sort_values(['cidade', 'data_iniSE']).copy()
    df['ano'] = df['data_iniSE'].dt.year
    df = df.merge(limiares(df, percentil), on=['cidade', 'ano'], how='left').drop(columns='ano')
    df['alto'] = (df['casos_est'] >= df['limiar']).where(df['casos_est'].notna())
    df['razao_limiar'] = np.log1p(df['casos_est']) - np.log1p(df['limiar'])
    por_cidade = df.groupby('cidade', sort=False)['alto']
    for h in HORIZONTES:
        df[f'alto_h{h}'] = por_cidade.shift(-h)
    return df


def episodios(alto):
    """Episódios de nível alto numa série semanal (lista de pares início, fim, em posições).

    Junta interrupções de até MAX_INTERRUPCAO semanas e descarta episódios com menos de
    MIN_SEMANAS_EPISODIO semanas. 'fim' é a última semana alta do episódio.
    """
    a = np.asarray(alto, dtype=bool)
    altas = np.flatnonzero(a)
    if len(altas) == 0:
        return []
    grupos, inicio, anterior = [], altas[0], altas[0]
    for i in altas[1:]:
        if i - anterior > MAX_INTERRUPCAO + 1:
            grupos.append((inicio, anterior))
            inicio = i
        anterior = i
    grupos.append((inicio, anterior))
    return [(i, f) for i, f in grupos if f - i + 1 >= MIN_SEMANAS_EPISODIO]
