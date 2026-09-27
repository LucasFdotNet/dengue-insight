"""Carregamento de dados e textos comuns ao painel."""
import os

import pandas as pd
import streamlit as st

from src.train import ARQUIVO_PREVISOES_PASSADAS

ROTULO_PAPEL = {"treino": "treino", "validacao": "validação"}
REGIAO_UF = {
    "AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste", "PE": "Nordeste",
    "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MS": "Centro-Oeste", "MT": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}
SETA = {"sobe": ("▲", "Subida", "#c0392b"), "estável": ("▶", "Estável", "#7f8c8d"), "cai": ("▼", "Queda", "#27ae60")}
FORMATO_DATA_HOVER = "%{x|%d/%m/%Y}: %{y:,.0f} casos"


@st.cache_data
def carregar_municipio(cidade):
    df = pd.read_csv(f"data/processed/{cidade}_processed.csv")
    df["data_iniSE"] = pd.to_datetime(df["data_iniSE"])
    return df


@st.cache_data
def carregar_previsoes_passadas():
    if not os.path.exists(ARQUIVO_PREVISOES_PASSADAS):
        return None
    return pd.read_csv(ARQUIVO_PREVISOES_PASSADAS, parse_dates=["data_alvo"])


@st.cache_data
def carregar_csv(caminho):
    return pd.read_csv(caminho) if os.path.exists(caminho) else None
