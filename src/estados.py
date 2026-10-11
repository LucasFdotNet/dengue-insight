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


def limiares(df, percentil=PERCENTIL_ALTO, minimo=MIN_CASOS_ALTO):
    """Limiar de cada município e ano (DataFrame com cidade, ano, limiar)."""
    linhas = []
    for cidade, g in df.groupby('cidade'):
        anos = g['data_iniSE'].dt.year
        for ano in sorted(anos.unique()):
            ate = max(ano, PRIMEIRO_ANO_TESTE)
            passado = g.loc[anos < ate, 'casos_est'].dropna()
            limiar = max(passado.quantile(percentil), minimo) if len(passado) else np.nan
            linhas.append({'cidade': cidade, 'ano': ano, 'limiar': limiar})
    return pd.DataFrame(linhas)


# --------------------------------------------------------------- três níveis

# Verde (normal), amarelo (elevado) e vermelho (epidêmico). Variantes comparadas em experimento_niveis.py:
#   A: percentis do histórico do município: amarelo a partir do 75, vermelho a partir do 90;
#   B: percentis: amarelo do 80 ao 97 (faixa em torno do 90), vermelho a partir do 97;
#   C: canal endêmico do Ministério da Saúde (Plano de Contingência Nacional para Dengue, Chikungunya
#      e Zika, 2025, seção 5; ver docs/referencias.md): para cada semana epidemiológica, a mediana e o
#      terceiro quartil (Q3) dos casos da mesma semana nos 5 anos anteriores; amarelo acima da
#      mediana (faixa de "mobilização" do plano) e vermelho acima do Q3 ("alerta").
#   D: MEM (Moving Epidemic Method), como o InfoDengue calcula (src/mem.py): amarelo a partir do
#      limiar pré-epidêmico e vermelho a partir do limiar epidêmico, recalculados a cada temporada
#      (semana 41 à 40) com as temporadas anteriores, sobre a incidência por 100 mil habitantes
#      (população do Censo 2022), com os mínimos de 5 e 10 casos do InfoDengue.
VARIANTES_NIVEIS = {'A': ('percentis', 0.75, 0.90), 'B': ('percentis', 0.80, 0.97), 'C': ('canal',), 'D': ('mem',)}
DESCRICAO_VARIANTES = {
    'A': 'percentis: amarelo ≥ p75, vermelho ≥ p90',
    'B': 'percentis: amarelo ≥ p80, vermelho ≥ p97',
    'C': 'canal endêmico (MS): amarelo > mediana, vermelho > Q3 dos 5 anos anteriores',
    'D': 'MEM (como o InfoDengue): amarelo ≥ limiar pré-epidêmico, vermelho ≥ limiar epidêmico',
}
MIN_CASOS_AMARELO = 5
NOMES_NIVEIS = ['verde', 'amarelo', 'vermelho']

# Canal endêmico: escolhas que o Plano de Contingência não define (registradas também no README)
ANOS_CANAL = 5          # anos anteriores usados (o plano usa os últimos 5)
# - anos epidêmicos NÃO são excluídos da série (o plano não manda excluir; excluir exigiria definir
#   "ano epidêmico" antes de ter o canal);
# - quartis pelo método linear do numpy (tipo 7 de Hyndman e Fan, o padrão do R e do Excel);
# - casos, e não incidência: com a população praticamente constante em 5 anos, a comparação é a mesma;
# - semanas com poucos casos: amarelo exige pelo menos MIN_CASOS_AMARELO casos e vermelho pelo menos
#   MIN_CASOS_ALTO (os mesmos mínimos do InfoDengue), para que 1 ou 2 casos numa semana em que a
#   mediana é zero não virem "alerta";
# - a semana epidemiológica 53 usa o canal da semana 52;
# - semanas de treino anteriores a 2015 usam o canal de 2010 a 2014 (como em limiares()).


def canal_endemico(df):
    """Mediana e Q3 dos casos de cada município, ano e semana epidemiológica, com os ANOS_CANAL anos anteriores."""
    d = pd.DataFrame({'cidade': df['cidade'], 'ano': df['SE'] // 100, 'semana': np.minimum(df['SE'] % 100, 52),
                      'casos': df['casos_est']})
    linhas = []
    for cidade, g in d.groupby('cidade'):
        for ano in sorted(g['ano'].unique()):
            ate = max(ano, PRIMEIRO_ANO_TESTE)
            ref = g[(g['ano'] >= ate - ANOS_CANAL) & (g['ano'] < ate)].dropna(subset=['casos'])
            q = ref.groupby('semana')['casos'].quantile([0.5, 0.75]).unstack()
            linhas.append(pd.DataFrame({'cidade': cidade, 'ano': ano, 'semana': q.index,
                                        'mediana': q[0.5].to_numpy(), 'q3': q[0.75].to_numpy()}))
    return pd.concat(linhas, ignore_index=True)


def limiares_mem_por_temporada(df):
    """Limiares MEM (em casos) de cada município e temporada, calculados com as temporadas anteriores.

    Temporada = semana 41 de um ano à 40 do seguinte, identificada pelo ano de início. As
    temporadas anteriores a 2014-2015 (a que contém o início da avaliação, 2015) usam as de
    2010-2011 a 2013-2014, como em limiares().
    """
    from src.cidades import CIDADES
    from src.mem import SEMANA_INICIO_TEMPORADA, limiares_mem, temporadas_do_municipio

    linhas = []
    for cidade, g in df.groupby('cidade'):
        g = g.sort_values('SE')
        pop = CIDADES[cidade]['populacao']
        incidencia = g['casos_est'].to_numpy() * 1e5 / pop
        se = g['SE'].to_numpy()
        inicio = np.where(se % 100 >= SEMANA_INICIO_TEMPORADA, se // 100, se // 100 - 1)
        for temporada in np.unique(inicio):
            ate = max(temporada, PRIMEIRO_ANO_TESTE - 1)
            pre, epi = limiares_mem(list(temporadas_do_municipio(se, incidencia, ate_temporada=ate).values()))
            linhas.append({'cidade': cidade, 'temporada': temporada,
                           'mem_pre': pre * pop / 1e5, 'mem_epi': epi * pop / 1e5})
    return pd.DataFrame(linhas)


def adicionar_niveis(df, variante):
    """Acrescenta limiar_amarelo, limiar_vermelho, faixa (0 verde, 1 amarelo, 2 vermelho), faixa_h1 a faixa_h4 e as
    distâncias aos limiares. "faixa", e não "nivel", porque nivel é o alerta do InfoDengue nos dados."""
    metodo = VARIANTES_NIVEIS[variante]
    df = df.sort_values(['cidade', 'data_iniSE']).copy()
    if metodo[0] == 'percentis':
        df['ano'] = df['data_iniSE'].dt.year
        for nome, p, minimo in [('amarelo', metodo[1], MIN_CASOS_AMARELO), ('vermelho', metodo[2], MIN_CASOS_ALTO)]:
            df = df.merge(limiares(df, p, minimo).rename(columns={'limiar': f'limiar_{nome}'}), on=['cidade', 'ano'],
                          how='left')
        df = df.drop(columns='ano')
        acima = {'amarelo': df['casos_est'] >= df['limiar_amarelo'], 'vermelho': df['casos_est'] >= df['limiar_vermelho']}
    elif metodo[0] == 'mem':
        from src.mem import SEMANA_INICIO_TEMPORADA
        se = df['SE']
        df['temporada'] = np.where(se % 100 >= SEMANA_INICIO_TEMPORADA, se // 100, se // 100 - 1)
        df = df.merge(limiares_mem_por_temporada(df), on=['cidade', 'temporada'], how='left').drop(columns='temporada')
        df['limiar_amarelo'] = np.maximum(df['mem_pre'], MIN_CASOS_AMARELO)
        df['limiar_vermelho'] = np.maximum(df['mem_epi'], MIN_CASOS_ALTO)
        acima = {'amarelo': df['casos_est'] >= df['limiar_amarelo'], 'vermelho': df['casos_est'] >= df['limiar_vermelho']}
    else:
        df['ano'], df['semana'] = df['SE'] // 100, np.minimum(df['SE'] % 100, 52)
        df = df.merge(canal_endemico(df), on=['cidade', 'ano', 'semana'], how='left').drop(columns=['ano', 'semana'])
        # "Acima" da mediana e do Q3, como no plano, com os mínimos de casos
        acima = {'amarelo': (df['casos_est'] > df['mediana']) & (df['casos_est'] >= MIN_CASOS_AMARELO),
                 'vermelho': (df['casos_est'] > df['q3']) & (df['casos_est'] >= MIN_CASOS_ALTO)}
        df['limiar_amarelo'] = np.maximum(df['mediana'], MIN_CASOS_AMARELO)
        df['limiar_vermelho'] = np.maximum(df['q3'], MIN_CASOS_ALTO)
    for nome in ('amarelo', 'vermelho'):
        df[f'razao_{nome}'] = np.log1p(df['casos_est']) - np.log1p(df[f'limiar_{nome}'])
    faixa = acima['amarelo'].astype(float) + acima['vermelho']
    df['faixa'] = faixa.where(df['casos_est'].notna())
    por_cidade = df.groupby('cidade', sort=False)['faixa']
    for h in HORIZONTES:
        df[f'faixa_h{h}'] = por_cidade.shift(-h)
    return df


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
