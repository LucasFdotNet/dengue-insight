"""Seção "Indicadores": previsões das próximas 4 semanas e gráfico de projeções."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from painel.dados import FORMATO_DATA_HOVER, SETA, carregar_previsoes_passadas, seletor_municipio
from src.cidades import CIDADES
from src.predict import get_predictions
from src.train import PRIMEIRO_ANO_TESTE

SEMANAS_ULTIMOS_12_MESES = 52
MAX_SEMANAS_COM_MARCADORES = 104


def _card(coluna, linha):
    seta, rotulo, cor = SETA[linha["tendencia"]]
    # Fontes proporcionais à largura da tela (clamp), sem quebra de linha na tendência
    coluna.markdown(f"""
<div style="border:1px solid rgba(49,51,63,0.2);border-radius:0.6rem;padding:1.1rem 1rem;min-height:9.5rem;
            display:flex;flex-direction:column;justify-content:space-between;margin-bottom:0.5rem">
  <div style="font-size:clamp(0.75rem,0.9vw,0.9rem);color:#6b6b6b">Semana de {linha['data']:%d/%m/%Y}</div>
  <div style="font-size:clamp(1.15rem,2vw,1.9rem);font-weight:700;color:{cor};white-space:nowrap;margin:0.6rem 0">
    {seta} {rotulo}</div>
  <div style="font-size:clamp(0.8rem,1vw,0.95rem);color:#444">≈ {linha['previsto']} casos
    <span style="color:#888;white-space:nowrap">(entre {linha['inferior']} e {linha['superior']})</span></div>
</div>""", unsafe_allow_html=True)


def pagina():
    st.title("Projeções de Casos de Dengue por Município")
    cidade, df = seletor_municipio("municipio_indicadores")
    if cidade is not None:
        mostrar(cidade, df)


def mostrar(cidade, df):
    info = CIDADES[cidade]
    previsoes, base, descartadas = get_predictions(df)
    if previsoes.empty:
        st.error("Não há modelos treinados. Execute `python -m src.train` e recarregue o painel.")
        return

    # ------------------------------------------------------------ Período e antecedência
    ultimos_12 = "Últimos 12 meses"
    todo = f"Todo o período (desde {PRIMEIRO_ANO_TESTE})"
    anos = [str(a) for a in range(base.year, PRIMEIRO_ANO_TESTE - 1, -1)]
    col_periodo, col_h = st.columns([1, 2])
    periodo = col_periodo.selectbox("Período:", [ultimos_12, todo] + anos)
    h = col_h.radio("Previsões passadas feitas com antecedência de:", list(previsoes["h"]),
                    format_func=lambda x: f"{x} semana" + ("s" if x > 1 else ""), horizontal=True)

    # ------------------------------------------------------------ Cards das próximas semanas
    for coluna, (_, linha) in zip(st.columns(len(previsoes)), previsoes.iterrows()):
        _card(coluna, linha)
    valor_base = df.loc[df["data_iniSE"] == base, "casos_est"].iloc[0]
    st.caption(f"Em relação à semana de {base:%d/%m/%Y} ({int(valor_base)} casos estimados). Subida ou queda: "
               "variação de mais de 20% e de 5 casos.")
    ultima = df.dropna(subset=["casos_est"])["data_iniSE"].max()

    # ------------------------------------------------------------ Gráfico
    if periodo == ultimos_12:
        inicio, fim = ultima - pd.Timedelta(weeks=SEMANAS_ULTIMOS_12_MESES - 1), ultima
    elif periodo == todo:
        inicio, fim = pd.Timestamp(f"{PRIMEIRO_ANO_TESTE}-01-01"), ultima
    else:
        inicio, fim = pd.Timestamp(f"{periodo}-01-01"), pd.Timestamp(f"{periodo}-12-31")

    janela = df[(df["data_iniSE"] >= inicio) & (df["data_iniSE"] <= min(fim, base))]
    modo = "lines+markers" if len(janela) <= MAX_SEMANAS_COM_MARCADORES else "lines"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=janela["data_iniSE"], y=janela["casos_est"], mode=modo,
                             name="Casos estimados (real)", line=dict(color="#0275d8"),
                             hovertemplate=FORMATO_DATA_HOVER + "<extra>Real</extra>"))
    incompletas = df[(df["data_iniSE"] >= base) & (df["data_iniSE"] <= fim) & (df["data_iniSE"] >= inicio)]
    if descartadas and len(incompletas) > 1:
        fig.add_trace(go.Scatter(x=incompletas["data_iniSE"], y=incompletas["casos_est"], mode="lines+markers",
                                 name="Semanas ainda incompletas", line=dict(color="#95a5a6", dash="dot"),
                                 hovertemplate=FORMATO_DATA_HOVER + "<extra>Incompleta</extra>"))

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
    if descartadas:
        st.info(f"O InfoDengue não publica a estimativa de casos atrasados (*nowcast*, ver o glossário em \"Detalhes do "
                f"Modelo\") para {info['nome']}, então as {descartadas} semanas mais recentes ainda estão incompletas "
                f"(em cinza no gráfico). As previsões partem da última semana considerada completa "
                f"({base:%d/%m/%Y}); por isso algumas semanas previstas já passaram.")
    if info["papel"] == "validacao":
        st.info(f"{info['nome']} é um município de validação: seus dados nunca foram usados no treino do modelo.")
    st.caption("As previsões acima são geradas por modelos analíticos e estão sujeitas a erro. A tendência e o "
               "número de casos vêm de modelos diferentes e podem divergir; o número é uma estimativa, com uma "
               "faixa que contém o valor real em cerca de 80% das semanas.")
