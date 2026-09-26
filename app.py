import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.cidades import CIDADES
from src.predict import get_predictions

# Colunas que o CSV processado precisa ter. Se faltar alguma, o app para com erro
# explícito em vez de exibir valores inventados.
COLUNAS_OBRIGATORIAS = ["data_iniSE", "casos_est", "casos_est_min", "casos_est_max", "tmin", "rt", "nivel"]
DIAS_DADOS_DESATUALIZADOS = 21

st.set_page_config(page_title="Dengue Insight | UNIVESP PI-IV", layout="wide")

st.title("🦟 Dengue Insight")
st.markdown("**Monitoramento e previsão de surtos de dengue (PI-IV UNIVESP)**")

# ---------------------------------------------------------------- Seleção do município
disponiveis = [k for k in CIDADES if os.path.exists(f"data/processed/{k}_processed.csv")]

if not disponiveis:
    st.error("Nenhum dado processado encontrado. Execute ingestion.py, preprocessing.py e train.py e recarregue o painel.")
    st.stop()

cidade = st.sidebar.selectbox(
    "Selecione o município:",
    disponiveis,
    format_func=lambda k: CIDADES[k]["nome"],
)
nome = CIDADES[cidade]["nome"]


@st.cache_data
def load_cidade_data(cidade):
    df = pd.read_csv(f"data/processed/{cidade}_processed.csv")
    df["data_iniSE"] = pd.to_datetime(df["data_iniSE"])
    return df


df_cidade = load_cidade_data(cidade)

faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df_cidade.columns]
if faltando:
    st.error(f"O arquivo processado de {nome} não tem as colunas: {', '.join(faltando)}. "
             "Verifique o rename_map em preprocessing.py e processe os dados novamente.")
    st.stop()

df_valid = df_cidade.dropna(subset=["casos_est"])
ultimo_registro = df_valid.iloc[-1]
ultima = ultimo_registro["data_iniSE"]

# ---------------------------------------------------------------- Indicadores da última semana
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

casos_val = int(ultimo_registro["casos_est"])

ajuda_casos = None
if pd.notnull(ultimo_registro["casos_est_min"]) and pd.notnull(ultimo_registro["casos_est_max"]):
    ajuda_casos = (f"Intervalo do nowcast: {int(ultimo_registro['casos_est_min'])}"
                   f"–{int(ultimo_registro['casos_est_max'])} casos")

col1.metric("Casos estimados", casos_val, help=ajuda_casos)
# O ERA5 chega com alguns dias de atraso; a semana mais recente pode ainda não ter clima
if pd.notnull(ultimo_registro["tmin"]):
    col2.metric("Temp. mínima", f"{ultimo_registro['tmin']:.1f} °C")
else:
    col2.metric("Temp. mínima", "sem dado", help="Dado climático (ERA5) ainda não disponível para esta semana")
col3.metric("Taxa reprodutiva (Rt)", f"{ultimo_registro['rt']:.2f}")
col4.metric("Nível de alerta", int(ultimo_registro["nivel"]))

st.caption(f"Última semana epidemiológica: {ultima:%d/%m/%Y}")
if (pd.Timestamp.today() - ultima).days > DIAS_DADOS_DESATUALIZADOS:
    st.warning("Os dados estão desatualizados. Execute a ingestão novamente para ver as semanas mais recentes.")

# ---------------------------------------------------------------- Histórico
st.markdown("### Histórico epidemiológico")

fig_hist = go.Figure()
# Faixa de incerteza do nowcast (visível apenas nas semanas recentes, ainda sujeitas a revisão)
fig_hist.add_trace(go.Scatter(
    x=df_valid["data_iniSE"], y=df_valid["casos_est_max"],
    mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
))
fig_hist.add_trace(go.Scatter(
    x=df_valid["data_iniSE"], y=df_valid["casos_est_min"],
    mode="lines", line=dict(width=0), fill="tonexty",
    fillcolor="rgba(217, 83, 79, 0.2)", name="Intervalo do nowcast", hoverinfo="skip",
))
fig_hist.add_trace(go.Scatter(
    x=df_valid["data_iniSE"], y=df_valid["casos_est"],
    mode="lines", line=dict(color="#d9534f", width=2), name="Casos estimados",
))
fig_hist.update_layout(
    title=f"Evolução temporal de casos – {nome}",
    xaxis_title="Semana", yaxis_title="Casos estimados",
)
st.plotly_chart(fig_hist, width="stretch")

# ---------------------------------------------------------------- Projeções
st.markdown("---")
st.markdown("### 🔮 Projeções de machine learning (próximas 4 semanas)")

predicoes, data_base = get_predictions(cidade, df_cidade)

if not predicoes:
    if CIDADES[cidade]["papel"] == "validacao":
        st.info(f"{nome} é um município de validação espacial, por isso não tem modelo próprio.")
    else:
        st.error(f"Não há modelo treinado para {nome}. Execute train.py e recarregue o painel.")
else:
    base = pd.to_datetime(data_base, dayfirst=True)
    valor_base = df_cidade.loc[df_cidade["data_iniSE"] == base, "casos_est"].iloc[0]
    st.caption(f"Previsões geradas a partir da semana de {base:%d/%m/%Y}.")

    # predict.py devolve chaves no formato "Semana +H (dd/mm/aaaa)"; extrai H de cada uma
    por_horizonte = {int(chave.split("+")[1].split(" ")[0]): valor for chave, valor in predicoes.items()}
    horizontes = sorted(por_horizonte)
    datas_futuras = [base + pd.Timedelta(weeks=h) for h in horizontes]
    valores_futuros = [por_horizonte[h] for h in horizontes]

    cols_pred = st.columns(len(horizontes))
    for col, h, data, valor in zip(cols_pred, horizontes, datas_futuras, valores_futuros):
        col.metric(
            label=f"Semana +{h} ({data:%d/%m/%Y})",
            value=valor,
            delta=int(valor - valor_base),
            delta_color="inverse",
        )

    hist_recente = df_cidade[df_cidade["data_iniSE"] <= base].tail(8)

    fig_proj = go.Figure()
    fig_proj.add_trace(go.Scatter(
        x=hist_recente["data_iniSE"], y=hist_recente["casos_est"],
        mode="lines+markers", name="Histórico recente", line=dict(color="#0275d8"),
    ))
    # A série prevista começa na última semana observada, para as duas linhas se conectarem
    fig_proj.add_trace(go.Scatter(
        x=[base] + datas_futuras, y=[valor_base] + valores_futuros,
        mode="lines+markers", name="Previsão (ML)", line=dict(color="#d9534f", dash="dash"),
    ))
    fig_proj.update_layout(xaxis_title="Semana", yaxis_title="Casos estimados")
    st.plotly_chart(fig_proj, width="stretch")