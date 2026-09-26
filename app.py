import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.cidades import CIDADES
from src.predict import get_predictions
from src.train import ARQUIVO_PREVISOES_PASSADAS, SEMANAS_INSTAVEIS

# Colunas que o CSV processado precisa ter. Se faltar alguma, o app para com erro
# explícito em vez de exibir valores inventados.
COLUNAS_OBRIGATORIAS = ["data_iniSE", "casos_est", "casos_est_min", "casos_est_max", "tmin", "rt", "nivel"]
DIAS_DADOS_DESATUALIZADOS = 21
SEMANAS_HISTORICO_PROJECAO = 52  # 12 meses de histórico no gráfico de projeções
ROTULO_PAPEL = {"treino": "treino", "validacao": "validação"}
FORMATO_DATA_HOVER = "%{x|%d/%m/%Y}: %{y:,.0f} casos"

st.set_page_config(page_title="Dengue Insight | UNIVESP PI-IV", layout="wide")

st.title("🦟 Dengue Insight")
st.markdown("**Monitoramento e previsão de surtos de dengue (PI-IV UNIVESP)**")

# ---------------------------------------------------------------- Seleção do município
disponiveis = [k for k in CIDADES if os.path.exists(f"data/processed/{k}_processed.csv")]

if not disponiveis:
    st.error("Nenhum dado processado encontrado. Execute ingestion.py, preprocessing.py e train.py e recarregue o painel.")
    st.stop()

tipo = st.sidebar.radio(
    "Tipo de município:",
    ["Todos", "Treino", "Validação espacial"],
    help="Treino: municípios usados para treinar o modelo. Validação espacial: municípios que o modelo "
         "nunca viu no treino, usados para testar se ele funciona em outras regiões.",
)
papel_filtro = {"Todos": None, "Treino": "treino", "Validação espacial": "validacao"}[tipo]
opcoes = [k for k in disponiveis if papel_filtro is None or CIDADES[k]["papel"] == papel_filtro]
if not opcoes:
    st.sidebar.warning("Nenhum município processado desse tipo.")
    st.stop()

cidade = st.sidebar.selectbox(
    "Selecione o município:",
    opcoes,
    format_func=lambda k: f"{CIDADES[k]['nome']} ({ROTULO_PAPEL[CIDADES[k]['papel']]})",
)
nome = CIDADES[cidade]["nome"]


@st.cache_data
def load_cidade_data(cidade):
    df = pd.read_csv(f"data/processed/{cidade}_processed.csv")
    df["data_iniSE"] = pd.to_datetime(df["data_iniSE"])
    return df


@st.cache_data
def load_previsoes_passadas():
    if not os.path.exists(ARQUIVO_PREVISOES_PASSADAS):
        return None
    return pd.read_csv(ARQUIVO_PREVISOES_PASSADAS, parse_dates=["data_alvo"])


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
    hovertemplate=FORMATO_DATA_HOVER + "<extra></extra>",
))
fig_hist.update_layout(
    title=f"Evolução temporal de casos – {nome}",
    xaxis_title="Semana epidemiológica (data de início)", yaxis_title="Casos estimados",
    xaxis_tickformat="%m/%Y",
)
st.plotly_chart(fig_hist, width="stretch")

with st.expander("O que são \"casos estimados\" e \"intervalo do nowcast\"?"):
    st.markdown(
        "- **Casos notificados** são os casos já registrados no sistema para uma semana. Nas semanas "
        "recentes esse número está incompleto, porque as notificações chegam com atraso: um caso desta "
        "semana pode entrar no sistema duas ou três semanas depois.\n"
        "- **Casos estimados** são a estimativa do InfoDengue de quantos casos aquela semana terá quando "
        "todas as notificações chegarem. Essa correção do presente pelo atraso das notificações se chama "
        "*nowcast*. Nas semanas antigas, já completas, o valor estimado é igual ao notificado.\n"
        "- **Intervalo do nowcast** é a margem de incerteza dessa estimativa: o número final deve ficar "
        "dentro da faixa. Por isso ela só aparece nas últimas semanas, e não aparece nos municípios em que "
        "o InfoDengue não calcula o nowcast.\n\n"
        "Cada ponto da série é uma **semana epidemiológica** (de domingo a sábado), a unidade em que o "
        "InfoDengue publica os dados. Os rótulos do eixo mostram meses apenas para facilitar a leitura."
    )

# ---------------------------------------------------------------- Projeções
st.markdown("---")
st.markdown("### 🔮 Projeções de machine learning (próximas 4 semanas)")

predicoes, data_base = get_predictions(cidade, df_cidade)

if not predicoes:
    st.error("Não há modelo treinado. Execute train.py e recarregue o painel.")
else:
    base = pd.to_datetime(data_base, dayfirst=True)
    valor_base = df_cidade.loc[df_cidade["data_iniSE"] == base, "casos_est"].iloc[0]
    st.caption(f"Previsões geradas a partir da semana de {base:%d/%m/%Y}.")
    if CIDADES[cidade]["papel"] == "validacao":
        st.info(f"{nome} é um município de validação espacial: seus dados não foram usados no treino do modelo.")

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

    hist_recente = df_cidade[df_cidade["data_iniSE"] <= base].tail(SEMANAS_HISTORICO_PROJECAO)
    inicio_janela = hist_recente["data_iniSE"].min()

    fig_proj = go.Figure()
    fig_proj.add_trace(go.Scatter(
        x=hist_recente["data_iniSE"], y=hist_recente["casos_est"],
        mode="lines+markers", name="Casos estimados (real)", line=dict(color="#0275d8"),
        hovertemplate=FORMATO_DATA_HOVER + "<extra>Real</extra>",
    ))

    # Previsões passadas: vêm da validação walk-forward, em que cada semana foi prevista por um
    # modelo treinado só com dados anteriores ao ano dela. Usar o modelo de produção aqui seria
    # enganoso, porque ele já viu essas semanas no treino.
    previsoes_passadas = load_previsoes_passadas()
    resumo_passado = None
    if previsoes_passadas is not None:
        h_passado = st.radio(
            "Previsões passadas feitas com antecedência de:",
            horizontes,
            format_func=lambda h: f"{h} semana" + ("s" if h > 1 else ""),
            horizontal=True,
        )
        passadas = previsoes_passadas[
            (previsoes_passadas["cidade"] == cidade)
            & (previsoes_passadas["h"] == h_passado)
            & (previsoes_passadas["data_alvo"] >= inicio_janela)
        ]
        if not passadas.empty:
            # Baseline de persistência: repete, para a semana alvo, os casos de H semanas antes
            casos_por_semana = df_cidade.set_index("data_iniSE")["casos_est"]
            baseline = casos_por_semana.reindex(passadas["data_alvo"] - pd.Timedelta(weeks=h_passado)).values
            fig_proj.add_trace(go.Scatter(
                x=passadas["data_alvo"], y=baseline,
                mode="lines", name=f"Baseline (repete o valor de {h_passado} sem. antes)",
                line=dict(color="#999999", width=1, dash="dot"),
                hovertemplate=FORMATO_DATA_HOVER + "<extra>Baseline</extra>",
            ))
            fig_proj.add_trace(go.Scatter(
                x=passadas["data_alvo"], y=passadas["previsto"],
                mode="lines+markers", name=f"Previsão passada ({h_passado} sem. antes)",
                line=dict(color="#d9534f", dash="dot"), marker=dict(size=4),
                hovertemplate=FORMATO_DATA_HOVER + "<extra>Previsão passada</extra>",
            ))
            erro_modelo = (passadas["real"] - passadas["previsto"]).abs().mean()
            erro_baseline = (passadas["real"] - baseline).abs().mean()
            resumo_passado = (
                f"Nas {len(passadas)} semanas com previsão passada exibidas, o modelo errou em média "
                f"**{erro_modelo:,.0f} casos por semana**; o baseline (repetir o valor de {h_passado} "
                f"semana(s) antes) errou **{erro_baseline:,.0f}**. As últimas semanas não têm previsão "
                f"passada porque os casos delas ainda estão sendo revisados ({SEMANAS_INSTAVEIS} semanas "
                f"instáveis)."
            )

    # A série prevista começa na última semana observada, para as duas linhas se conectarem
    fig_proj.add_trace(go.Scatter(
        x=[base] + datas_futuras, y=[valor_base] + valores_futuros,
        mode="lines+markers", name="Previsão (próximas semanas)",
        line=dict(color="#d9534f", dash="dash", width=3),
        hovertemplate=FORMATO_DATA_HOVER + "<extra>Previsão</extra>",
    ))
    fig_proj.update_layout(
        xaxis_title="Semana epidemiológica (data de início)", yaxis_title="Casos estimados",
        xaxis_tickformat="%m/%Y", margin=dict(t=30),
        legend=dict(orientation="h", yanchor="top", y=-0.2),
    )
    st.plotly_chart(fig_proj, width="stretch")
    if resumo_passado:
        st.caption(resumo_passado)

    with st.expander("Como as previsões passadas foram geradas?"):
        st.markdown(
            "As previsões passadas mostram o que o modelo **teria previsto na época**, sem conhecer o futuro. "
            "Elas vêm da validação *walk-forward*: para cada ano, um modelo foi treinado só com os dados "
            "anteriores a esse ano e usado para prever as semanas dele. Assim, nenhuma semana exibida foi "
            "vista pelo modelo que a previu.\n\n"
            "O **baseline** é a previsão mais simples possível: repetir o número de casos de algumas semanas "
            "antes. O modelo só é útil se errar menos que ele."
        )
