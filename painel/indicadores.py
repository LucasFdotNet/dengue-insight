"""Seção "Indicadores": previsões das próximas 4 semanas e gráfico de projeções."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel.dados import FORMATO_DATA_HOVER, SETA, carregar_previsoes_passadas
from src.cidades import CIDADES
from src.predict import get_predictions
from src.train import PRIMEIRO_ANO_TESTE

SEMANAS_ULTIMOS_12_MESES = 52
MAX_SEMANAS_COM_MARCADORES = 104


def _card(coluna, linha):
    seta, rotulo, cor = SETA[linha["tendencia"]]
    with coluna.container(border=True):
        st.caption(f"Semana de {linha['data']:%d/%m/%Y}")
        st.markdown(f"<div style='font-size:1.9rem;font-weight:700;color:{cor};line-height:1.2'>"
                    f"{seta} {rotulo}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.95rem;color:#555'>≈ {linha['previsto']} casos "
                    f"<span style='color:#888'>(entre {linha['inferior']} e {linha['superior']})</span></div>",
                    unsafe_allow_html=True)


def mostrar(cidade, df):
    info = CIDADES[cidade]
    st.title("Projeções de Casos de Dengue por Município")
    st.subheader(f"{info['nome']} - {info['uf']}")
    st.caption("As previsões abaixo são geradas por modelos analíticos e estão sujeitas a erro. A tendência e o "
               "número de casos vêm de modelos diferentes e podem divergir; o número é uma estimativa, com uma "
               "faixa que contém o valor real em cerca de 80% das semanas.")
    if info["papel"] == "validacao":
        st.info(f"{info['nome']} é um município de validação: seus dados nunca foram usados no treino do modelo.")

    previsoes, base = get_predictions(df)
    if previsoes.empty:
        st.error("Não há modelos treinados. Execute `python -m src.train` e recarregue o painel.")
        return

    # ------------------------------------------------------------ Cards das próximas semanas
    for coluna, (_, linha) in zip(st.columns(len(previsoes)), previsoes.iterrows()):
        _card(coluna, linha)
    valor_base = df.loc[df["data_iniSE"] == base, "casos_est"].iloc[0]
    st.caption(f"Em relação à semana de {base:%d/%m/%Y} ({int(valor_base)} casos estimados). Subida ou queda: "
               "variação de mais de 20% e de 5 casos.")

    # ------------------------------------------------------------ Gráfico
    ultimos_12 = "Últimos 12 meses"
    todo = f"Todo o período (desde {PRIMEIRO_ANO_TESTE})"
    anos = [str(a) for a in range(base.year, PRIMEIRO_ANO_TESTE - 1, -1)]
    col_periodo, col_h = st.columns([1, 2])
    periodo = col_periodo.selectbox("Período:", [ultimos_12, todo] + anos)
    h = col_h.radio("Previsões passadas feitas com antecedência de:", list(previsoes["h"]),
                    format_func=lambda x: f"{x} semana" + ("s" if x > 1 else ""), horizontal=True)
    if periodo == ultimos_12:
        inicio, fim = base - pd.Timedelta(weeks=SEMANAS_ULTIMOS_12_MESES - 1), base
    elif periodo == todo:
        inicio, fim = pd.Timestamp(f"{PRIMEIRO_ANO_TESTE}-01-01"), base
    else:
        inicio, fim = pd.Timestamp(f"{periodo}-01-01"), pd.Timestamp(f"{periodo}-12-31")

    janela = df[(df["data_iniSE"] >= inicio) & (df["data_iniSE"] <= min(fim, base))]
    modo = "lines+markers" if len(janela) <= MAX_SEMANAS_COM_MARCADORES else "lines"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=janela["data_iniSE"], y=janela["casos_est"], mode=modo,
                             name="Casos estimados (real)", line=dict(color="#0275d8"),
                             hovertemplate=FORMATO_DATA_HOVER + "<extra>Real</extra>"))

    passadas = carregar_previsoes_passadas()
    if passadas is not None:
        p = passadas[(passadas["cidade"] == cidade) & (passadas["h"] == h)
                     & (passadas["data_alvo"] >= inicio) & (passadas["data_alvo"] <= fim)]
        fig.add_trace(go.Scatter(x=p["data_alvo"], y=p["previsto"], mode=modo,
                                 name=f"Previsão passada ({h} sem. antes)",
                                 line=dict(color="#d9534f", dash="dot"), marker=dict(size=4),
                                 hovertemplate=FORMATO_DATA_HOVER + "<extra>Previsão passada</extra>"))

    if periodo == ultimos_12:
        datas = [base] + list(previsoes["data"])
        fig.add_trace(go.Scatter(x=datas, y=[valor_base] + list(previsoes["superior"]), mode="lines",
                                 line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=datas, y=[valor_base] + list(previsoes["inferior"]), mode="lines",
                                 line=dict(width=0), fill="tonexty", fillcolor="rgba(217,83,79,0.15)",
                                 name="Faixa da previsão (80%)", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=datas, y=[valor_base] + list(previsoes["previsto"]), mode="lines+markers",
                                 name="Previsão (próximas semanas)", line=dict(color="#d9534f", dash="dash", width=3),
                                 hovertemplate=FORMATO_DATA_HOVER + "<extra>Previsão</extra>"))

    fig.update_layout(xaxis_title="Semana epidemiológica (data de início)", yaxis_title="Casos",
                      xaxis_tickformat="%m/%Y", margin=dict(t=30),
                      legend=dict(orientation="h", yanchor="top", y=-0.2))
    st.plotly_chart(fig, width="stretch")
    st.caption("Previsão passada: o que o modelo teria previsto na época, sem conhecer o futuro (retreinado a cada "
               "mês só com os dados disponíveis até então). As últimas semanas não têm previsão passada porque "
               "os casos delas ainda estão sendo revisados. Detalhes e acerto por município em \"Detalhes do Modelo\".")
