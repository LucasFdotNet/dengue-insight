import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from src.predict import get_predictions

st.set_page_config(page_title="Dengue Insight | UNIVESP PI-IV", layout="wide")

st.title("🦟 Dengue Insight")
st.markdown("**Monitoramento e Previsao de Surtos de Dengue (PI-IV UNIVESP)**")

cidades_disponiveis = [f.split('_')[0] for f in os.listdir('data/processed') if f.endswith('.csv')] if os.path.exists('data/processed') else []

if not cidades_disponiveis:
    st.error("Execute os scripts de ingestao, processamento e treino antes de carregar o painel.")
    st.stop()

cidade_selecionada = st.sidebar.selectbox("Selecione o Municipio:", [c.capitalize() for c in sorted(cidades_disponiveis)])

@st.cache_data
def load_cidade_data(cidade):
    df = pd.read_csv(f"data/processed/{cidade.lower()}_processed.csv")
    df['data_iniSE'] = pd.to_datetime(df['data_iniSE'])
    return df

df_cidade = load_cidade_data(cidade_selecionada)
df_valid = df_cidade.dropna(subset=['casos_est'])
ultimo_registro = df_valid.iloc[-1]

st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

# Métricas seguras com fallback se o campo não existir
casos_val = int(ultimo_registro['casos_est']) if 'casos_est' in ultimo_registro else 0
tmin_val = f"{ultimo_registro['tmin']} °C" if 'tmin' in ultimo_registro else "N/D"
rt_val = round(float(ultimo_registro['rt']), 2) if 'rt' in ultimo_registro and pd.notnull(ultimo_registro['rt']) else "1.00"
nivel_val = int(ultimo_registro['nivel']) if 'nivel' in ultimo_registro and pd.notnull(ultimo_registro['nivel']) else 1

col1.metric("Casos Estimados", casos_val)
col2.metric("Temp. Minima", tmin_val)
col3.metric("Taxa Reprodutiva (Rt)", rt_val)
col4.metric("Nivel de Alerta", nivel_val)

st.markdown("### Historico Epidemiologico")
fig_hist = px.line(
    df_valid, x='data_iniSE', y='casos_est',
    title=f"Evolucao Temporal de Casos - {cidade_selecionada}",
    labels={'data_iniSE': 'Data da Semana', 'casos_est': 'Casos Estimados'}
)
fig_hist.update_traces(line=dict(color='#d9534f', width=2))
st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("---")
st.markdown("### 🔮 Projecoes de Machine Learning (Proximas 4 Semanas)")

predicoes, data_base = get_predictions(cidade_selecionada.lower(), df_cidade)

if predicoes:
    st.caption(f"Previsoes geradas a partir dos dados da semana de {data_base}.")
    cols_pred = st.columns(len(predicoes))
    for i, (periodo, valor) in enumerate(predicoes.items()):
        delta = valor - casos_val
        with cols_pred[i]:
            st.metric(label=periodo, value=valor, delta=delta, delta_color="inverse")
            
    datas_futuras = [p.split('(')[1].replace(')','') for p in predicoes.keys()]
    valores_futuros = list(predicoes.values())
    
    hist_recente = df_valid.tail(4)
    datas_contexto = hist_recente['data_iniSE'].dt.strftime("%d/%m/%Y").tolist()
    valores_contexto = hist_recente['casos_est'].tolist()
    
    fig_proj = go.Figure()
    fig_proj.add_trace(go.Scatter(x=datas_contexto, y=valores_contexto, mode='lines+markers', name='Historico Recente', line=dict(color='#0275d8')))
    fig_proj.add_trace(go.Scatter(x=datas_futuras, y=valores_futuros, mode='lines+markers', name='Previsao (ML)', line=dict(color='#d9534f', dash='dash')))
    fig_proj.update_layout(xaxis_title="Semana", yaxis_title="Casos Estimados")
    st.plotly_chart(fig_proj, use_container_width=True)