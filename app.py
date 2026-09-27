"""Painel do Dengue Insight (Streamlit): aviso de entrada, seleção do município e seções."""
import os

import streamlit as st

from painel import detalhes, indicadores
from painel.dados import ROTULO_PAPEL, carregar_municipio
from src.cidades import CIDADES

# Colunas que o CSV processado precisa ter. Se faltar alguma, o app para com erro
# explícito em vez de exibir valores inventados.
COLUNAS_OBRIGATORIAS = ["data_iniSE", "casos_est", "casos_est_min", "casos_est_max", "tmin", "rt", "nivel"]
AVISO = ("Este painel é resultado de um trabalho acadêmico (Projeto Integrador IV, UNIVESP). As previsões são "
         "experimentais e **não devem ser usadas como base para decisões oficiais de vigilância ou de saúde pública**.")
PALAVRA_ACEITE = "entendo"

st.set_page_config(page_title="Dengue Insight | UNIVESP PI-IV", layout="wide")

# ---------------------------------------------------------------- Aviso de entrada
# Validação só no navegador (sessão do Streamlit), sem registro no servidor
if not st.session_state.get("aviso_aceito"):
    st.title("🦟 Dengue Insight")
    st.warning(AVISO)
    with st.form("aceite"):
        texto = st.text_input(f"Para continuar, digite \"{PALAVRA_ACEITE}\":")
        if st.form_submit_button("Continuar"):
            if texto.strip().lower() == PALAVRA_ACEITE:
                st.session_state["aviso_aceito"] = True
                st.rerun()
            st.error(f"Digite \"{PALAVRA_ACEITE}\" para continuar.")
    st.stop()

# ---------------------------------------------------------------- Menu e seleção do município
st.sidebar.title("🦟 Dengue Insight")
secao = st.sidebar.radio("Seção:", ["Indicadores", "Detalhes do Modelo"])
st.sidebar.markdown("---")

disponiveis = [k for k in CIDADES if os.path.exists(f"data/processed/{k}_processed.csv")]
if not disponiveis:
    st.error("Nenhum dado processado encontrado. Execute ingestion.py, preprocessing.py e train.py e recarregue o painel.")
    st.stop()

tipo = st.sidebar.radio(
    "Tipo de município:", ["Todos", "Treino", "Validação espacial"],
    help="Treino: municípios usados para treinar o modelo. Validação espacial: municípios que o modelo "
         "nunca viu no treino, usados para testar se ele funciona em outras regiões.",
)
papel_filtro = {"Todos": None, "Treino": "treino", "Validação espacial": "validacao"}[tipo]
opcoes = [k for k in disponiveis if papel_filtro is None or CIDADES[k]["papel"] == papel_filtro]
if not opcoes:
    st.sidebar.warning("Nenhum município processado desse tipo.")
    st.stop()
cidade = st.sidebar.selectbox(
    "Município:", opcoes,
    format_func=lambda k: f"{CIDADES[k]['nome']} - {CIDADES[k]['uf']} ({ROTULO_PAPEL[CIDADES[k]['papel']]})",
)
st.sidebar.caption("Trabalho acadêmico (PI-IV, UNIVESP). Previsões experimentais.")

df = carregar_municipio(cidade)
faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
if faltando:
    st.error(f"O arquivo processado de {CIDADES[cidade]['nome']} não tem as colunas: {', '.join(faltando)}. "
             "Processe os dados novamente.")
    st.stop()

if secao == "Indicadores":
    indicadores.mostrar(cidade, df)
else:
    detalhes.mostrar(cidade, df)
