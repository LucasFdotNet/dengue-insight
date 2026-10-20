"""
Experimento: níveis pelos limiares fixos de incidência do Ministério da Saúde x pelo MEM.

O Ministério da Saúde classifica a incidência de dengue em baixa (menos de 100 casos por 100 mil
habitantes), média (100 a 300) e alta (300 ou mais), sobre a incidência ACUMULADA nas 4 últimas
semanas (boletins epidemiológicos; por exemplo, o 17º boletim de 2025 da Secretaria de Saúde do
Espírito Santo). Os limiares são os mesmos em todo o país e dispensam o cálculo do MEM. Aqui:

1. Descrição: com que frequência cada nível aparece se os limiares forem aplicados à incidência da
   semana (definição E de src/estados.py), à acumulada em 4 semanas, na temporada (semana 41 à 40)
   e em 52 semanas, comparado com o MEM (definição D); em quantos municípios o nível alto nunca
   aparece ou aparece quase sempre; quantas vezes o nível alto termina (a desmobilização).
2. Modelo: o mesmo modelo do painel (quantis de casos com o clima; experimento_niveis_quantis.py),
   sem treinar de novo (só a previsão de 1 semana à frente, que o painel não usa). Ele prevê casos,
   e a chance de cada nível sai da faixa prevista lida nos limiares. Definição F (a do Ministério):
   a soma de 4 semanas junta semanas já conhecidas e previstas; os quantis da soma são a soma dos
   quantis de cada semana prevista (supõe que as semanas sobem e descem juntas, o que alarga um
   pouco a faixa) mais os casos já conhecidos. Definição E (a semana sozinha), para mostrar o efeito
   do período: limiares de 100 e 300 casos por 100 mil na semana. Avaliação
   como em experimento_niveis_robustez.py (alerta, desmobilização e nível, com o corte do alerta
   escolhido de novo pelo mesmo critério), sem atraso e com 2 semanas de atraso, de 2019 em diante,
   com IC 95% por bootstrap sobre municípios. As variáveis de distância aos limiares do modelo
   continuam as do MEM (retreinar com as do Ministério poderia mudar um pouco o resultado).

A acumulada na temporada e a de 52 semanas não entram no modelo: a primeira só sobe até a semana 41
(nunca há desmobilização dentro da temporada), e as duas deixam a maior parte dos municípios no nível
alto quase o tempo todo.

3. Calendário: as métricas de 2. medem o alerta contra o início da epidemia de cada definição, e a
   acumulada em 4 semanas começa depois (mediana de 2 semanas depois do MEM). Para comparar quando o
   gestor seria avisado, toma-se cada epidemia pelo MEM (2 semanas de atraso) e mede-se, para o
   alerta de cada definição, se ele veio até o início dela, 2 semanas antes ou mais, ou se não veio
   até 4 semanas depois.

Saídas: reports/niveis_ms.csv (métricas), reports/niveis_ms_descricao.csv (frequência dos níveis) e
reports/niveis_ms_calendario.csv (alerta em relação ao início pelo MEM)

Resultado: o MEM avisou mais epidemias e mais cedo; continua (seção 26 de docs/historia_decisoes.md). Fora do
pipeline completo (usa o cache do modelo do painel; cerca de 10 minutos).

Uso: python -m src.experimento_niveis_ms
"""
import logging

import numpy as np
import pandas as pd

from src import experimento_niveis as en
from src import experimento_niveis_quantis as enq
from src import experimento_niveis_robustez as enr
from src.cidades import CIDADES
from src.modelos.lightgbm_quantis_niveis import probabilidades_niveis
from src.snapshot import id_dados_processados

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

LIMIARES_MS = (100, 300)  # casos por 100 mil habitantes
LACUNAS = [0, 2]
INICIO_DESCRICAO = '2015-01-01'
SEMENTE = 42
ARQUIVO_SAIDA = 'reports/niveis_ms.csv'
ARQUIVO_DESCRICAO = 'reports/niveis_ms_descricao.csv'
ARQUIVO_CALENDARIO = 'reports/niveis_ms_calendario.csv'
JANELA_ANTES, JANELA_DEPOIS = 8, 4  # semanas em torno do início da epidemia pelo MEM
EMISSAO = {}  # tabelas por semana de emissão com 2 semanas de atraso, para o calendário
DEFINICOES = {'D': 'MEM (atual)', 'F': 'Ministério da Saúde, acumulada em 4 semanas',
              'E': 'Ministério da Saúde, incidência da semana'}
SEMANAS_ACUMULADAS = 4


# --------------------------------------------------------------- descrição

def nivel_ms(incidencia):
    return np.where(incidencia >= LIMIARES_MS[1], 2, np.where(incidencia >= LIMIARES_MS[0], 1, 0)).astype(float)


def descricao():
    """Frequência dos níveis, municípios sempre ou nunca no nível alto e fins do nível alto, por definição."""
    treino, validacao = en.dados('D')
    b = pd.concat([treino, validacao], ignore_index=True).sort_values(['cidade', 'data_iniSE'])
    b = b[(b['data_iniSE'] >= INICIO_DESCRICAO) & b['casos_est'].notna()].copy()
    b['inc'] = b['casos_est'] * 1e5 / b['cidade'].map(lambda c: CIDADES[c]['populacao'])
    se = b['SE']
    b['temporada'] = np.where(se % 100 >= 41, se // 100, se // 100 - 1)
    g = b.groupby('cidade')['inc']
    niveis = {
        'MEM, semana (D)': b['faixa'],
        'Ministério, semana (E)': nivel_ms(b['inc']),
        'Ministério, acumulada em 4 semanas (F)': nivel_ms(g.transform(lambda s: s.rolling(4, min_periods=4).sum())),
        'Ministério, acumulada na temporada': nivel_ms(b.groupby(['cidade', 'temporada'])['inc'].cumsum()),
        'Ministério, acumulada em 52 semanas': nivel_ms(g.transform(lambda s: s.rolling(52, min_periods=52).sum())),
    }
    linhas = []
    for nome, nivel in niveis.items():
        x = b[['cidade']].assign(nivel=np.asarray(nivel, float)).dropna()
        alto = x['nivel'] == 2
        por_mun = alto.groupby(x['cidade']).mean()
        # Fins do nível alto: semanas em que o nível sai do alto (o alto da semana anterior, no mesmo município)
        anterior = x.groupby('cidade')['nivel'].shift(1)
        fins = ((anterior == 2) & (x['nivel'] < 2)).groupby(x['cidade']).sum()
        linhas.append({'definicao': nome, 'semanas': len(x),
                       'baixa_verde': (x['nivel'] == 0).mean(), 'media_amarelo': (x['nivel'] == 1).mean(),
                       'alta_vermelho': alto.mean(),
                       'municipios_nunca_alto': int((por_mun == 0).sum()),
                       'municipios_alto_mais_de_metade': int((por_mun > 0.5).sum()),
                       'fins_do_alto_por_municipio_ano': fins.sum() / (len(x) / 52.18)})
    return pd.DataFrame(linhas)


# --------------------------------------------------------------- modelo

def quantis_acumulados(id_, p):
    """Quantis da soma dos casos nas 4 semanas que terminam em S+h (h de 2 a 8), a partir da semana S.

    Semanas até S: casos conhecidos; semanas depois de S: soma dos quantis previstos de cada uma.
    """
    colunas = enq.colunas_q(enq.VARIANTE_PRODUCAO)
    h1 = enq.rodar_previsoes(id_, enq.VARIANTE_PRODUCAO, enq.PROCESSOS, [1], f'{enq.VARIANTE_PRODUCAO}_h1')
    q = pd.concat([h1, p[['cidade', 'data_iniSE', 'h'] + colunas]], ignore_index=True)
    largo = {h: g.set_index(['cidade', 'data_iniSE'])[colunas] for h, g in q.groupby('h')}
    treino, validacao = enq.dados()
    b = pd.concat([treino, validacao], ignore_index=True).sort_values(['cidade', 'data_iniSE'])
    passado = {k: b.groupby('cidade')['casos_est'].shift(k).set_axis(pd.MultiIndex.from_frame(b[['cidade', 'data_iniSE']]))
               for k in range(SEMANAS_ACUMULADAS - 1)}  # casos de S-k
    partes = []
    for h in sorted(p['h'].unique()):
        semanas = range(h - SEMANAS_ACUMULADAS + 1, h + 1)  # S+h-3 a S+h, a partir de S
        indice = largo[h].index
        for k in semanas:
            if k >= 1:
                indice = indice.intersection(largo[k].index)
        soma = np.zeros((len(indice), len(colunas)))
        for k in semanas:
            soma += largo[k].reindex(indice).to_numpy() if k >= 1 else passado[-k].reindex(indice).to_numpy()[:, None]
        parte = pd.DataFrame(soma, columns=colunas, index=indice).reset_index().assign(h=h)
        partes.append(parte.dropna())
    return pd.concat(partes, ignore_index=True)


def chances(id_, definicao):
    """Previsões fora da amostra do modelo do painel, com a chance de cada nível pela definição pedida."""
    p = enq.previsoes_producao(id_)
    if definicao == 'D':
        return p[['cidade', 'data_iniSE', 'h', 'p0', 'p1', 'p2']]
    if definicao == 'F':
        p = quantis_acumulados(id_, p)
    pop = p['cidade'].map(lambda c: CIDADES[c]['populacao']).to_numpy(float)
    q = p[enq.colunas_q(enq.VARIANTE_PRODUCAO)].to_numpy()
    c = probabilidades_niveis(q, LIMIARES_MS[0] * pop / 1e5, LIMIARES_MS[1] * pop / 1e5,
                              enq.VARIANTES[enq.VARIANTE_PRODUCAO]['grade'])
    return p[['cidade', 'data_iniSE', 'h']].assign(p0=c[:, 0], p1=c[:, 1], p2=c[:, 2])


def calendario(emissao):
    """Para cada epidemia pelo MEM, a semana do 1º alerta de cada definição, em relação ao início dela."""
    chave = ['cidade', 'data_iniSE']
    b = emissao['D'][chave + ['conjunto', 'alto']]
    for d, s in emissao.items():
        b = b.merge(s[chave + ['modelo_alerta']].rename(columns={'modelo_alerta': f'alerta_{d}'}), on=chave)
    b = b[b['data_iniSE'] >= enr.ee.INICIO_AVALIACAO].sort_values(chave)
    linhas = []
    for cidade, g in b.groupby('cidade'):
        alto = g['alto'].fillna(False).to_numpy(bool)
        for i, _ in enr.episodios(alto):
            if i < JANELA_ANTES:
                continue
            janela = slice(i - JANELA_ANTES, i + JANELA_DEPOIS + 1)
            linha = {'conjunto': g['conjunto'].iloc[0], 'cidade': cidade}
            for d in emissao:
                semanas = np.flatnonzero(g[f'alerta_{d}'].fillna(False).to_numpy(bool)[janela])
                linha[d] = semanas[0] - JANELA_ANTES if len(semanas) else np.nan
            linhas.append(linha)
    t = pd.DataFrame(linhas)
    saida = []
    for conjunto, x in t.groupby('conjunto'):
        for d in emissao:
            v = x[d]
            saida.append({'definicao': DEFINICOES[d], 'conjunto': conjunto, 'epidemias_mem': len(x),
                          'alerta_ate_o_inicio': (v <= 0).mean(), 'alerta_2_semanas_antes': (v <= -2).mean(),
                          'sem_alerta_ate_4_semanas_depois': v.isna().mean(),
                          'semana_do_1o_alerta_mediana': v.median()})
    return pd.DataFrame(saida)


def avaliar(definicao, prev, lacuna, rng):
    treino, validacao = en.dados(definicao)
    s = enr.tabela_emissao(prev, pd.concat([treino, validacao], ignore_index=True), lacuna)
    if lacuna == 2:
        EMISSAO[definicao] = s.drop(columns=[]).copy()
        EMISSAO[definicao].attrs = {}
    linhas = []
    for conjunto, gc in s.groupby('conjunto'):
        cidades = gc.groupby('cidade', sort=True)
        base = {'definicao': DEFINICOES[definicao], 'conjunto': conjunto, 'lacuna': lacuna}
        testes = [('mobilizacao', 'modelo_alerta', enr.componentes_alerta, enr.metricas_alerta),
                  ('mobilizacao_regra', 'regra', enr.componentes_alerta, enr.metricas_alerta),
                  ('desmobilizacao', 'saida_modelo', enr.componentes_desmobilizacao, enr.metricas_desmobilizacao)]
        for teste, sinal, componentes, metricas in testes:
            comp = pd.DataFrame({c: componentes(g, sinal, lacuna) for c, g in cidades}).T
            for linha in enr.com_ic(comp, metricas, rng=rng):
                linhas.append({**base, 'teste': teste, **linha})
            if teste == 'mobilizacao':
                linhas.append({**base, 'teste': teste, 'metrica': 'episodios', 'valor': comp['episodios'].sum(),
                               'municipios': len(comp)})
        for h in en.HORIZONTES_NIVEIS:
            comp = pd.DataFrame({c: enr.componentes_nivel(g, h) for c, g in cidades}).T
            for linha in enr.com_ic(comp, enr.metricas_nivel, rng=rng):
                linhas.append({**base, 'teste': f'nivel_{h}_semanas', **linha})
        corte = s.attrs['cortes'].sort_values('trimestre').iloc[-1]['corte_alerta']
        linhas.append({**base, 'teste': 'mobilizacao', 'metrica': 'corte_alerta_atual', 'valor': corte})
    return linhas


def run_experimento():
    d = descricao()
    d.round(4).to_csv(ARQUIVO_DESCRICAO, index=False)
    pd.set_option('display.width', 250)
    print(d.round(3).to_string(index=False))
    id_ = id_dados_processados()
    rng = np.random.default_rng(SEMENTE)
    linhas = []
    for definicao in DEFINICOES:
        prev = chances(id_, definicao)
        for lacuna in LACUNAS:
            logging.info(f"Definição {definicao}, lacuna {lacuna}...")
            linhas += avaliar(definicao, prev, lacuna, rng)
    r = pd.DataFrame(linhas)
    r = r[['definicao', 'teste', 'conjunto', 'lacuna', 'metrica', 'valor', 'ic95_inf', 'ic95_sup', 'municipios']]
    r.round(4).to_csv(ARQUIVO_SAIDA, index=False)
    print(r.round(3).to_string(index=False))
    c = calendario(EMISSAO)
    c.round(4).to_csv(ARQUIVO_CALENDARIO, index=False)
    print(c.round(3).to_string(index=False))


if __name__ == "__main__":
    run_experimento()
