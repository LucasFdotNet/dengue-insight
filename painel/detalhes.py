"""Seção "Detalhes do Modelo": modelo atual, comparação com outros modelos, municípios e dados do município."""
import os

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from painel.dados import (FORMATO_DATA_HOVER, REGIAO_UF, ROTULO_PAPEL, carregar_csv, carregar_previsoes_passadas)
from src.cidades import CIDADES
from src.train import HORIZONTES, TENDENCIAS, caminho_modelo

# Modelos exibidos na comparação (nome no CSV -> rótulo); a ordem define a ordem nos gráficos
MODELOS = {
    "baseline_persistencia": "Baseline (sempre estável)",
    "sinal_rt": "Regra do Rt (InfoDengue)",
    "sinal_p_rt1": "Regra do p_rt1 (InfoDengue)",
    "classificador_rt": "Classificador só com o Rt",
    "regressao_linear": "Regressão linear",
    "binomial_negativa": "Binomial negativa",
    "ensemble": "Ensemble",
    "lightgbm_quantis": "LightGBM por quantis (usado: número de casos)",
    "lightgbm_atual": "LightGBM de regressão",
    "lightgbm_ajustado": "LightGBM ajustado",
    "lightgbm_classificador": "LightGBM classificador sem clima",
    "lightgbm_classificador_clima_s1_s4": "LightGBM classificador com clima (usado: tendência)",
}
EM_USO = {"lightgbm_quantis", "lightgbm_classificador_clima_s1_s4"}
ARQUIVOS_METRICAS = ["reports/comparacao_modelos.csv", "reports/comparacao_rt.csv",
                     "reports/comparacao_clima_classificador.csv"]
ARQUIVOS_POR_MUNICIPIO = ["reports/comparacao_modelos_por_municipio.csv", "reports/comparacao_rt_por_municipio.csv",
                          "reports/comparacao_clima_classificador_por_municipio.csv"]
NOMES_VARIAVEIS = {"log_casos": "Casos atuais (log)", "semana_ano": "Semana do ano",
                   **{f"var_log_{k}": f"Variação em relação a {k} sem. atrás" for k in range(1, 5)},
                   **{f"tmed_s{k}": f"Temperatura média (S-{k})" for k in range(1, 6)},
                   **{f"precipitacao_s{k}": f"Chuva (S-{k})" for k in range(1, 6)},
                   **{f"umidade_s{k}": f"Umidade (S-{k})" for k in range(1, 6)}}
CONJUNTOS = {"validacao_cruzada": "Validação cruzada (100 municípios de treino)",
             "validacao_final": "Validação final (15 municípios nunca usados no treino)"}


def _juntar(arquivos):
    partes = [carregar_csv(a) for a in arquivos]
    partes = [p for p in partes if p is not None]
    if not partes:
        return None
    return pd.concat(partes, ignore_index=True).drop_duplicates(subset=None)


def _baixar(df, nome, rotulo="Baixar tabela (CSV)"):
    st.download_button(rotulo, df.to_csv(index=False).encode("utf-8-sig"), file_name=nome, mime="text/csv",
                       key=f"baixar_{nome}")


# ---------------------------------------------------------------- 1. Modelo atual

def _modelo_atual():
    st.markdown("""
O painel usa **dois modelos**, ambos do tipo LightGBM (conjuntos de árvores de decisão), treinados com os
**100 municípios de treino** de todo o Brasil e um modelo para cada antecedência (1 a 4 semanas):

| | Tendência (seta dos cards) | Número de casos (valor e faixa dos cards) |
|---|---|---|
| **Modelo** | LightGBM **classificador** | LightGBM **por quantis** |
| **O que prevê** | Se os casos vão subir, ficar estáveis ou cair | Mediana dos casos e faixa de 80% ("entre X e Y") |
| **Informações usadas** | Casos atuais, variação em relação a 1 a 4 semanas atrás, semana do ano e clima das 4 semanas anteriores (temperatura, chuva e umidade) | Casos atuais, variação em relação a 1 a 4 semanas atrás e semana do ano |
| **Por que foi escolhido** | Melhor acerto de tendência entre 12 alternativas; detecta mais subidas | Menor erro no número de casos e faixa bem calibrada |

**Como a tendência é definida:** comparando os casos daqui a H semanas com os da semana atual, é **subida** ou
**queda** quando a variação passa de 20% e de 5 casos; caso contrário, **estável**.

**O que não é usado:** o Rt do InfoDengue (serve só para comparação) e o nome do município (por isso o modelo
pode prever municípios que nunca viu).

**Como foi avaliado:** simulação do uso real (*walk-forward*): a cada mês desde 2015, os modelos são treinados
só com o que já era conhecido e preveem as semanas seguintes. Os municípios de validação nunca entram no treino.
""")
    st.markdown("#### Desempenho do modelo em uso")
    tend = carregar_csv("reports/metricas_tendencia.csv")
    gerais = carregar_csv("reports/metricas_gerais.csv")
    if tend is not None and gerais is not None:
        t = tend.merge(gerais[["Grupo", "Horizonte", "Razao_MAE"]], on=["Grupo", "Horizonte"])
        t["Grupo"] = t["Grupo"].map({"treino": "Treino (100)", "validacao": "Validação (15)"})
        exibir = t[["Grupo", "Horizonte", "Acerto_balanceado", "Acerto", "Acerto_sempre_estavel", "Subidas_detectadas",
                    "Alarmes_subida_corretos", "Sentido_oposto", "Razao_MAE"]]
        exibir.columns = ["Municípios", "Antecedência", "Acerto balanceado", "Acerto", "Acerto do \"sempre estável\"",
                          "Subidas detectadas", "Alarmes de subida corretos", "Sentido oposto", "Razão de erro em casos"]
        st.dataframe(exibir.style.format({c: "{:.1%}" for c in exibir.columns[3:8]} |
                                         {"Acerto balanceado": "{:.3f}", "Razão de erro em casos": "{:.2f}"}),
                     hide_index=True, width="stretch")
        _baixar(exibir, "desempenho_modelo_em_uso.csv")

    with st.expander("Como ler as métricas", expanded=False):
        st.markdown("""
* **Acerto balanceado** (de 0 a 1, maior é melhor): média do acerto em cada situação (subiu, ficou estável,
  caiu), calculado separadamente. Dizer sempre "estável" tira 0,333. Exemplo: acertar 42% das subidas, 75% das
  semanas estáveis e 61% das quedas dá (42% + 75% + 61%) / 3 = 0,59.
* **Acerto** (maior é melhor): fração das semanas com a tendência certa. Deve ser comparado com o "sempre
  estável", que já acerta muito porque a maioria das semanas é estável.
* **Subidas detectadas**: das semanas em que os casos subiram, em quantas o modelo previu subida.
* **Alarmes de subida corretos**: das vezes em que o modelo previu subida, em quantas os casos subiram.
* **Sentido oposto** (menor é melhor): semanas em que o modelo previu subida e os casos caíram, ou o contrário.
* **Razão de erro em casos** (menor é melhor): erro médio do modelo de quantis dividido pelo erro de repetir
  os casos atuais. Abaixo de 1, o modelo é melhor.
""")

    st.markdown("#### O que mais pesa nas previsões")
    st.caption("Importância de cada informação para o modelo (ganho total nas árvores, em % do total). "
               "Mostra o que o modelo usa mais, não uma relação de causa.")
    h = st.radio("Antecedência:", list(HORIZONTES), format_func=lambda x: f"{x} semana" + ("s" if x > 1 else ""),
                 horizontal=True, key="importancia_h")
    colunas = st.columns(2)
    for coluna, (tipo, titulo) in zip(colunas, [("classificador", "Classificador (tendência)"),
                                                ("quantis", "Quantis (número de casos, mediana)")]):
        caminho = caminho_modelo(tipo, h)
        if not os.path.exists(caminho):
            coluna.warning("Modelo não treinado.")
            continue
        modelo = joblib.load(caminho)
        lgbm = modelo.modelo if tipo == "classificador" else modelo.modelos["previsto"]
        ganho = lgbm.booster_.feature_importance(importance_type="gain")
        imp = pd.DataFrame({"variavel": [NOMES_VARIAVEIS.get(f, f) for f in lgbm.booster_.feature_name()],
                            "importancia": ganho / ganho.sum()}).sort_values("importancia")
        fig = px.bar(imp, x="importancia", y="variavel", orientation="h", title=titulo,
                     labels={"importancia": "Importância (% do total)", "variavel": ""})
        fig.update_layout(xaxis_tickformat=".0%", height=420, margin=dict(l=10, r=10, t=40, b=10))
        coluna.plotly_chart(fig, width="stretch")

    st.markdown("""
#### Limitações
* **Dados revisados:** a avaliação usa os casos já consolidados. Em tempo real, as semanas recentes ainda estão
  incompletas e o modelo erraria mais. Num teste sem as 4 semanas mais recentes, o erro cresceu de 1,6 a 2,8
  vezes, mas o modelo continuou melhor que repetir o último valor conhecido.
* **Generalização desigual:** o modelo vai bem na maioria dos municípios de validação, mas empata com o baseline
  em alguns do Norte (Parauapebas, Manacapuru) e em Caruaru e Sinop.
* **Seleção por surtos:** 37 municípios de treino foram escolhidos pelo histórico de epidemias, o que pode deixar o
  modelo mais propenso a prever subidas.
""")


# ---------------------------------------------------------------- 2. Comparação de modelos

def _comparacao():
    metricas = _juntar(ARQUIVOS_METRICAS)
    por_municipio = _juntar(ARQUIVOS_POR_MUNICIPIO)
    if metricas is None or por_municipio is None:
        st.warning("Resultados da comparação não encontrados. Rode `python -m src.experimento_modelos`, "
                   "`python -m src.experimento_rt` e `python -m src.experimento_clima_classificador`.")
        return
    metricas = metricas[metricas["modelo"].isin(MODELOS)].drop_duplicates(["modelo", "conjunto", "h", "metrica"])
    por_municipio = por_municipio[por_municipio["modelo"].isin(MODELOS)].drop_duplicates(
        ["modelo", "conjunto", "cidade", "h"])

    st.markdown("12 modelos avaliados da mesma forma, com as mesmas semanas (2019 em diante). A escolha foi feita "
                "pela **validação cruzada** nos 100 municípios de treino; a validação final só confirma.")
    c1, c2 = st.columns([2, 1])
    conjunto = c1.radio("Avaliação:", list(CONJUNTOS), format_func=CONJUNTOS.get, horizontal=True)
    h = c2.selectbox("Antecedência:", list(HORIZONTES), index=3, format_func=lambda x: f"{x} semana" + ("s" if x > 1 else ""))

    m = metricas[(metricas["conjunto"] == conjunto)]
    ordem = [MODELOS[k] for k in MODELOS if k in set(m["modelo"])]

    # Acerto balanceado com IC 95%
    ab = m[(m["metrica"] == "acerto_balanceado") & (m["h"] == h)].copy()
    ab["Modelo"] = ab["modelo"].map(MODELOS)
    ab["Em uso"] = np.where(ab["modelo"].isin(EM_USO), "Em uso no painel", "Alternativa")
    fig = px.bar(ab, x="valor", y="Modelo", orientation="h", color="Em uso",
                 color_discrete_map={"Em uso no painel": "#d9534f", "Alternativa": "#95a5a6"},
                 error_x=ab["ic95_sup"] - ab["valor"], error_x_minus=ab["valor"] - ab["ic95_inf"],
                 category_orders={"Modelo": ordem},
                 title=f"Acerto balanceado da tendência, {h} semana(s) de antecedência",
                 labels={"valor": "Acerto balanceado (maior é melhor; baseline = 0,333)", "Modelo": ""})
    fig.add_vline(x=1 / 3, line_dash="dot", line_color="#555")
    fig.update_layout(height=480, legend_title_text="", margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, width="stretch")
    st.caption("Barras de erro: intervalo de confiança de 95% (bootstrap sobre municípios). "
               "Use o ícone de câmera no canto do gráfico para baixá-lo como imagem.")

    # Evolução por antecedência
    ev = m[m["metrica"] == "acerto_balanceado"].copy()
    ev["Modelo"] = ev["modelo"].map(MODELOS)
    fig = px.line(ev, x="h", y="valor", color="Modelo", markers=True, category_orders={"Modelo": ordem},
                  title="Acerto balanceado por antecedência",
                  labels={"h": "Antecedência (semanas)", "valor": "Acerto balanceado"})
    fig.update_layout(xaxis_dtick=1, height=460, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, width="stretch")

    # Tabela completa
    st.markdown(f"#### Todas as métricas ({h} semana(s) de antecedência)")
    tab = m[m["h"] == h].pivot_table(index="modelo", columns="metrica", values="valor")
    tab = tab.reindex([k for k in MODELOS if k in tab.index])
    tab.index = tab.index.map(MODELOS)
    nomes = {"acerto_balanceado": "Acerto balanceado", "acerto": "Acerto", "subidas_detectadas": "Subidas detectadas",
             "alarmes_subida_corretos": "Alarmes de subida corretos", "quedas_detectadas": "Quedas detectadas",
             "sentido_oposto": "Sentido oposto", "razao_mae": "Razão de erro em casos",
             "cobertura_intervalo_80": "Cobertura da faixa de 80%"}
    tab = tab[[c for c in nomes if c in tab.columns]].rename(columns=nomes).reset_index(names="Modelo")
    st.dataframe(tab.style.format({c: "{:.3f}" for c in tab.columns[1:]}, na_rep="—"), hide_index=True, width="stretch")
    _baixar(tab, f"comparacao_modelos_{conjunto}_h{h}.csv")

    # Matrizes de confusão
    st.markdown(f"#### Matrizes de confusão ({h} semana(s) de antecedência)")
    st.caption("Linhas: o que aconteceu. Colunas: o que o modelo previu. Cada linha soma 100%; a diagonal são os acertos.")
    escolha_padrao = ["lightgbm_classificador_clima_s1_s4", "lightgbm_quantis", "classificador_rt", "baseline_persistencia"]
    disponiveis = [k for k in MODELOS if k in set(por_municipio["modelo"])]
    escolhidos = st.multiselect("Modelos:", disponiveis, default=[k for k in escolha_padrao if k in disponiveis],
                                format_func=MODELOS.get)
    pm = por_municipio[(por_municipio["conjunto"] == conjunto) & (por_municipio["h"] == h)]
    for inicio in range(0, len(escolhidos), 2):
        for coluna, modelo in zip(st.columns(2), escolhidos[inicio:inicio + 2]):
            soma = pm[pm["modelo"] == modelo].sum(numeric_only=True)
            matriz = np.array([[soma[f"real_{r}_prev_{p}"] for p in TENDENCIAS] for r in TENDENCIAS])
            linhas = matriz / matriz.sum(axis=1, keepdims=True)
            rotulos = ["Subiu", "Estável", "Caiu"]
            texto = [[f"{linhas[i, j]:.0%}<br>({int(matriz[i, j]):,})".replace(",", ".") for j in range(3)] for i in range(3)]
            fig = go.Figure(go.Heatmap(z=linhas, x=["Previu subida", "Previu estável", "Previu queda"], y=rotulos,
                                       text=texto, texttemplate="%{text}", colorscale="Reds", zmin=0, zmax=1,
                                       showscale=False))
            fig.update_layout(title=MODELOS[modelo], yaxis_autorange="reversed", height=340,
                              margin=dict(l=10, r=10, t=50, b=10))
            coluna.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------- 3. Municípios

def _municipios():
    df = pd.DataFrame([{**v, "chave": k} for k, v in CIDADES.items()])
    df["Região"] = df["uf"].map(REGIAO_UF)
    df["Papel"] = df["papel"].map({"treino": "Treino", "validacao": "Validação"})
    st.markdown(f"**{len(df)} municípios**: {int((df['papel'] == 'treino').sum())} de treino e "
                f"{int((df['papel'] == 'validacao').sum())} de validação (nunca usados no treino). "
                "Critérios de seleção no README do projeto (decisão 1).")
    fig = px.scatter_map(df, lat="lat", lon="lon", color="Papel", size="populacao", size_max=22,
                         hover_name="nome", hover_data={"uf": True, "populacao": ":,", "lat": False, "lon": False},
                         color_discrete_map={"Treino": "#0275d8", "Validação": "#d9534f"},
                         center=dict(lat=-14.5, lon=-52), zoom=3.1, map_style="carto-positron",
                         title="Municípios do projeto (tamanho do ponto proporcional à população)")
    fig.update_layout(height=650, margin=dict(l=0, r=0, t=50, b=0))
    st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    por_regiao = df.pivot_table(index="Região", columns="Papel", values="chave", aggfunc="count", fill_value=0)
    por_regiao["Total"] = por_regiao.sum(axis=1)
    c1.markdown("**Por região**")
    c1.dataframe(por_regiao, width="stretch")
    fig = px.bar(df.groupby(["uf", "Papel"]).size().reset_index(name="Municípios"), x="uf", y="Municípios",
                 color="Papel", color_discrete_map={"Treino": "#0275d8", "Validação": "#d9534f"},
                 title="Por UF", labels={"uf": "UF"})
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), xaxis={"categoryorder": "total descending"})
    c2.plotly_chart(fig, width="stretch")
    lista = df[["nome", "uf", "Região", "Papel", "populacao", "criterio"]].rename(
        columns={"nome": "Município", "uf": "UF", "populacao": "População (2022)", "criterio": "Critério de inclusão"})
    with st.expander("Lista completa"):
        st.dataframe(lista, hide_index=True, width="stretch")
    _baixar(lista, "municipios.csv", "Baixar lista (CSV)")


# ---------------------------------------------------------------- 4. Município selecionado

def _municipio(cidade, df):
    info = CIDADES[cidade]
    st.markdown(f"#### {info['nome']} - {info['uf']} ({ROTULO_PAPEL[info['papel']]})")
    ultimo = df.dropna(subset=["casos_est"]).iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    ajuda = None
    if pd.notnull(ultimo["casos_est_min"]) and pd.notnull(ultimo["casos_est_max"]):
        ajuda = f"Intervalo do nowcast: {int(ultimo['casos_est_min'])}–{int(ultimo['casos_est_max'])} casos"
    c1.metric("Casos estimados", int(ultimo["casos_est"]), help=ajuda)
    c2.metric("Temp. mínima", f"{ultimo['tmin']:.1f} °C" if pd.notnull(ultimo["tmin"]) else "sem dado")
    c3.metric("Rt (InfoDengue)", f"{ultimo['rt']:.2f}", help="Indicador do InfoDengue; não é usado pelo modelo.")
    c4.metric("Nível de alerta (InfoDengue)", int(ultimo["nivel"]))
    st.caption(f"Última semana epidemiológica: {ultimo['data_iniSE']:%d/%m/%Y}")

    validos = df.dropna(subset=["casos_est"])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=validos["data_iniSE"], y=validos["casos_est_max"], mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=validos["data_iniSE"], y=validos["casos_est_min"], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor="rgba(217,83,79,0.2)", name="Intervalo do nowcast",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=validos["data_iniSE"], y=validos["casos_est"], mode="lines",
                             line=dict(color="#d9534f", width=2), name="Casos estimados",
                             hovertemplate=FORMATO_DATA_HOVER + "<extra></extra>"))
    fig.update_layout(title="Histórico completo desde 2010", xaxis_tickformat="%m/%Y", yaxis_title="Casos estimados",
                      margin=dict(t=40))
    st.plotly_chart(fig, width="stretch")
    with st.expander("O que são \"casos estimados\" e \"intervalo do nowcast\"?"):
        st.markdown(
            "- **Casos notificados**: casos já registrados no sistema. Nas semanas recentes, estão incompletos, "
            "porque as notificações chegam com atraso.\n"
            "- **Casos estimados** (*nowcast*): estimativa do InfoDengue de quantos casos a semana terá quando "
            "todas as notificações chegarem. Nas semanas antigas, é igual ao notificado.\n"
            "- **Intervalo do nowcast**: margem de incerteza dessa estimativa; só aparece nas semanas recentes.")

    st.markdown("#### Acerto de tendência neste município")
    passadas = carregar_previsoes_passadas()
    if passadas is None:
        return
    c1, c2 = st.columns(2)
    h = c1.selectbox("Antecedência:", list(HORIZONTES), index=3, key="acerto_h",
                     format_func=lambda x: f"{x} semana" + ("s" if x > 1 else ""))
    anos = sorted(passadas["data_alvo"].dt.year.unique(), reverse=True)
    periodo = c2.selectbox("Período:", ["Todo o período"] + [str(a) for a in anos], key="acerto_periodo")
    p = passadas[(passadas["cidade"] == cidade) & (passadas["h"] == h)]
    if periodo != "Todo o período":
        p = p[p["data_alvo"].dt.year == int(periodo)]
    if p.empty:
        st.info("Sem previsões passadas para este recorte.")
        return
    real, prev = p["tend_real"], p["tend_prev"]
    acertos = [(prev[real == t] == t).mean() for t in TENDENCIAS if (real == t).any()]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Acerto balanceado", f"{np.mean(acertos):.2f}", help="De 0 a 1; o \"sempre estável\" tira 0,33.")
    k2.metric("Acerto", f"{(real == prev).mean():.0%}", help=f"\"Sempre estável\": {(real == 'estável').mean():.0%}")
    k3.metric("Subidas detectadas", f"{(prev[real == 'sobe'] == 'sobe').mean():.0%}" if (real == "sobe").any() else "—")
    k4.metric("Alarmes de subida corretos", f"{(real[prev == 'sobe'] == 'sobe').mean():.0%}" if (prev == "sobe").any() else "—")
    contagem = pd.crosstab(pd.Categorical(real, TENDENCIAS), pd.Categorical(prev, TENDENCIAS), dropna=False)
    percentual = contagem.div(contagem.sum(axis=1).replace(0, np.nan), axis=0)
    tabela = contagem.astype(str) + percentual.map(lambda v: f" ({v:.0%})" if pd.notnull(v) else "")
    tabela.index = [f"Aconteceu: {t}" for t in TENDENCIAS]
    tabela.columns = [f"Modelo previu: {t}" for t in TENDENCIAS]
    st.table(tabela)
    st.caption(f"{len(p)} semanas. Tendência prevista pelo classificador, retreinado a cada mês só com os dados "
               "disponíveis até então.")


def mostrar(cidade, df):
    st.title("Detalhes do Modelo")
    abas = st.tabs(["Modelo atual", "Comparação com outros modelos", "Municípios", "Dados do município selecionado"])
    with abas[0]:
        _modelo_atual()
    with abas[1]:
        _comparacao()
    with abas[2]:
        _municipios()
    with abas[3]:
        _municipio(cidade, df)
