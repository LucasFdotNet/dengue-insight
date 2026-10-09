"""Carregamento de dados e textos comuns ao painel."""
import os
import unicodedata

import pandas as pd
import streamlit as st

from src.cidades import CIDADES
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


COLUNAS_OBRIGATORIAS = ["data_iniSE", "casos_est", "casos_est_min", "casos_est_max", "tmin", "rt", "nivel"]
MUNICIPIO_PADRAO = "campinas"
GRUPO = {"treino": "Treino", "validacao": "Validação"}


def _ordem(chave):
    info = CIDADES[chave]
    nome = unicodedata.normalize("NFKD", info["nome"]).encode("ascii", "ignore").decode().lower()
    return (0 if info["papel"] == "treino" else 1, nome)


CABECALHO = "grupo:"  # prefixo das opções que são só títulos de grupo
RECUO = " "  # espaço largo: não é colapsado no HTML, ao contrário do espaço comum


def _rotulo(opcao):
    if opcao.startswith(CABECALHO):
        return f"{GRUPO[opcao[len(CABECALHO):]]}:"
    return f"{RECUO}{CIDADES[opcao]['nome']} - {CIDADES[opcao]['uf']}"


def _trocar_cabecalho(chave_widget, opcoes):
    """Se um título de grupo for escolhido, seleciona o primeiro município daquele grupo."""
    escolha = st.session_state[chave_widget]
    if escolha.startswith(CABECALHO):
        st.session_state[chave_widget] = opcoes[opcoes.index(escolha) + 1]


def seletor_municipio(chave_widget):
    """Seleção do município, agrupada por papel (treino, validação) e em ordem alfabética.

    O Streamlit não tem grupos (optgroup) no seletor; cada grupo entra na lista como uma opção de
    título, com os municípios recuados abaixo dele. A escolha é guardada em
    st.session_state["municipio"] e compartilhada entre as páginas. Devolve a chave do município e
    seus dados processados, ou None se não houver dados.
    """
    disponiveis = sorted([k for k in CIDADES if os.path.exists(f"data/processed/{k}_processed.csv")], key=_ordem)
    if not disponiveis:
        st.error("Nenhum dado processado encontrado. Execute ingestion.py, preprocessing.py e train.py.")
        return None, None
    opcoes, papel_anterior = [], None
    for k in disponiveis:
        papel = CIDADES[k]["papel"]
        if papel != papel_anterior:
            opcoes.append(CABECALHO + papel)
            papel_anterior = papel
        opcoes.append(k)
    atual = st.session_state.get("municipio", MUNICIPIO_PADRAO)
    cidade = st.selectbox(
        "Município:", opcoes, index=opcoes.index(atual) if atual in disponiveis else 1,
        format_func=_rotulo, key=chave_widget, on_change=_trocar_cabecalho, args=(chave_widget, opcoes),
        help="Treino: municípios usados para treinar o modelo. Validação: municípios que o modelo nunca viu no "
             "treino, usados para testar se ele funciona em outras regiões. Digite para buscar.",
    )
    st.session_state["municipio"] = cidade
    df = carregar_municipio(cidade)
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        st.error(f"O arquivo processado de {CIDADES[cidade]['nome']} não tem as colunas: {', '.join(faltando)}. "
                 "Processe os dados novamente.")
        return None, None
    return cidade, df
