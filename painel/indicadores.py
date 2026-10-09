"""Seção "Indicadores": previsões das próximas 4 semanas e gráfico de projeções."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from painel.dados import FORMATO_DATA_HOVER, SETA, carregar_previsoes_passadas, grafico, seletor_municipio
from src.cidades import CIDADES
from src.predict import get_predictions
from src.train import PRIMEIRO_ANO_TESTE, SEMANAS_INSTAVEIS

SEMANAS_ULTIMOS_12_MESES = 52
MAX_SEMANAS_COM_MARCADORES = 104
# Faixas de tendência abaixo do gráfico. "Aconteceu" e "Previu" são retângulos de uma semana (a largura
# acompanha o eixo de datas, então funciona de 12 meses a todo o período), com as cores dos cards;
# "Resultado" usa bolinhas, para não confundir o verde/vermelho de acerto com o de queda/subida.
FAIXAS = {"Aconteceu": 2, "Previu": 1, "Resultado": 0}
LARGURA_SEMANA_MS = 0.8 * 7 * 24 * 3600 * 1000
COR_ACERTO, COR_ERRO = "#27ae60", "#c0392b"


def _semanas(n):
    return f"{n} semana" + ("s" if n > 1 else "")


def _tendencia(t):
    return f"{SETA[t][0]} {SETA[t][1]}"


def _faixas_tendencia(fig, p):
    """Três faixas na parte de baixo do gráfico, uma marca por semana: tendência real, prevista e se acertou."""
    certo = p["tend_real"] == p["tend_prev"]
    dica = [("Acertou" if c else "Errou") + f": previu {_tendencia(a)}, aconteceu {_tendencia(b)}"
            for c, a, b in zip(certo, p["tend_prev"], p["tend_real"])]
    hover = "%{x|%d/%m/%Y}<br>%{customdata}<extra></extra>"
    for faixa, coluna in [("Aconteceu", "tend_real"), ("Previu", "tend_prev")]:
        fig.add_trace(go.Bar(x=p["data_alvo"], y=[0.7] * len(p), base=FAIXAS[faixa] - 0.35,
                             width=LARGURA_SEMANA_MS, marker_color=[SETA[t][2] for t in p[coluna]],
                             showlegend=False, customdata=dica, hovertemplate=hover), row=2, col=1)
    fig.add_trace(go.Scatter(x=p["data_alvo"], y=[FAIXAS["Resultado"]] * len(p), mode="markers", showlegend=False,
                             marker=dict(color=[COR_ACERTO if c else COR_ERRO for c in certo],
                                         size=7 if len(p) <= SEMANAS_ULTIMOS_12_MESES + 10 else 4),
                             customdata=dica, hovertemplate=hover), row=2, col=1)
    legenda = "   ".join([f"<span style='color:{cor}'>■</span> {rotulo}" for _, rotulo, cor in SETA.values()]
                         + [f"<span style='color:{COR_ACERTO}'>●</span> acertou",
                            f"<span style='color:{COR_ERRO}'>●</span> errou"])
    fig.add_annotation(text=f"Tendência:   {legenda}", xref="paper", yref="y2 domain", x=0, y=1,
                       xanchor="left", yanchor="bottom", showarrow=False, font=dict(size=12, color="#6b6b6b"))
    fig.update_yaxes(range=[-0.6, 2.6], tickvals=list(FAIXAS.values()), ticktext=list(FAIXAS),
                     tickfont=dict(size=11), showgrid=False, zeroline=False, row=2, col=1)


def _resumo_acerto(p, h, recorte):
    certos = p["tend_real"] == p["tend_prev"]
    subidas = p["tend_real"] == "sobe"
    # Subidas em destaque: é o erro que mais importa para a vigilância
    if subidas.any():
        st.markdown(f"<p style='font-size:1.2rem;font-weight:700;margin-bottom:0.25rem'>Subidas previstas: "
                    f"{(p.loc[subidas, 'tend_prev'] == 'sobe').sum()} de {subidas.sum()}</p>", unsafe_allow_html=True)
    texto = (f"{recorte}, com {_semanas(h)} de antecedência, o modelo acertou a tendência em "
             f"{certos.sum()} de {len(p)} semanas ({certos.mean():.0%}); dizer sempre \"estável\" acertaria "
             f"{(p['tend_real'] == 'estável').mean():.0%}.")
    alarmes_falsos = ((p["tend_prev"] == "sobe") & ~subidas).sum()
    if alarmes_falsos:
        texto += f" Alarmes de subida que não se confirmaram: {alarmes_falsos}."
    st.markdown(texto)


# Grade dos cards: 4 por linha, 2 em telas estreitas (mesmo limite em que o Streamlit empilha colunas).
# Fontes proporcionais à largura da tela (clamp), sem quebra de linha na tendência.
ESTILO_CARDS = """<style>
.cards-previsao {display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:0.5rem}
.card-previsao {border:1px solid rgba(49,51,63,0.2);border-radius:0.6rem;padding:1.1rem 1rem;min-height:9.5rem;
                display:flex;flex-direction:column;justify-content:space-between}
.card-previsao .data {font-size:clamp(0.75rem,0.9vw,0.9rem);color:#6b6b6b}
.card-previsao .tendencia {font-size:clamp(1.15rem,2vw,1.9rem);font-weight:700;white-space:nowrap;margin:0.6rem 0}
.card-previsao .casos {font-size:clamp(0.8rem,1vw,0.95rem);color:#444}
.card-previsao .faixa {color:#888;white-space:nowrap}
@media (max-width:640px) {
  .cards-previsao {grid-template-columns:repeat(2,1fr);gap:0.6rem}
  .card-previsao {padding:0.8rem 0.7rem;min-height:0}
  .card-previsao .tendencia {margin:0.4rem 0}
}
</style>"""


def _card(linha):
    seta, rotulo, cor = SETA[linha["tendencia"]]
    return f"""<div class="card-previsao">
  <div class="data">Semana de {linha['data']:%d/%m/%Y}</div>
  <div class="tendencia" style="color:{cor}">{seta} {rotulo}</div>
  <div class="casos">≈ {linha['previsto']} casos <span class="faixa">(entre {linha['inferior']} e {linha['superior']})</span></div>
</div>"""


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

    # ------------------------------------------------------------ Cards das próximas semanas
    cards = "".join(_card(linha) for _, linha in previsoes.iterrows())
    st.markdown(f'{ESTILO_CARDS}<div class="cards-previsao">{cards}</div>', unsafe_allow_html=True)
    valor_base = df.loc[df["data_iniSE"] == base, "casos_est"].iloc[0]
    st.caption(f"Em relação à semana de {base:%d/%m/%Y} ({int(valor_base)} casos estimados). Subida ou queda: "
               "variação de mais de 20% e de 5 casos.")
    ultima = df.dropna(subset=["casos_est"])["data_iniSE"].max()

    # ------------------------------------------------------------ Gráfico
    h = st.radio("Previsões passadas feitas com antecedência de:", list(previsoes["h"]),
                 format_func=_semanas, horizontal=True)
    ultimos_12 = "Últimos 12 meses"
    todo = f"Todo o período (desde {PRIMEIRO_ANO_TESTE})"
    anos = [str(a) for a in range(base.year, PRIMEIRO_ANO_TESTE - 1, -1)]
    col_periodo, _ = st.columns([1, 2])
    periodo = col_periodo.selectbox("Período:", [ultimos_12, todo] + anos)
    if periodo == ultimos_12:
        inicio, fim = ultima - pd.Timedelta(weeks=SEMANAS_ULTIMOS_12_MESES - 1), ultima
        recorte = "Nos últimos 12 meses"
    elif periodo == todo:
        inicio, fim = pd.Timestamp(f"{PRIMEIRO_ANO_TESTE}-01-01"), ultima
        recorte = f"Desde {PRIMEIRO_ANO_TESTE}"
    else:
        inicio, fim = pd.Timestamp(f"{periodo}-01-01"), pd.Timestamp(f"{periodo}-12-31")
        recorte = f"Em {periodo}"

    janela = df[(df["data_iniSE"] >= inicio) & (df["data_iniSE"] <= min(fim, base))]
    modo = "lines+markers" if len(janela) <= MAX_SEMANAS_COM_MARCADORES else "lines"
    # Em cima: casos; embaixo: faixas de tendência (mesmo eixo de datas)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.07)
    fig.add_trace(go.Scatter(x=janela["data_iniSE"], y=janela["casos_est"], mode=modo,
                             name="Casos estimados (real)", line=dict(color="#0275d8"),
                             hovertemplate=FORMATO_DATA_HOVER + "<extra>Real</extra>"))
    incompletas = df[(df["data_iniSE"] >= base) & (df["data_iniSE"] <= fim) & (df["data_iniSE"] >= inicio)]
    if descartadas and len(incompletas) > 1:
        fig.add_trace(go.Scatter(x=incompletas["data_iniSE"], y=incompletas["casos_est"], mode="lines+markers",
                                 name="Semanas ainda incompletas", line=dict(color="#95a5a6", dash="dot"),
                                 hovertemplate=FORMATO_DATA_HOVER + "<extra>Incompleta</extra>"))

    passadas = carregar_previsoes_passadas()
    p = pd.DataFrame()
    if passadas is not None:
        p = passadas[(passadas["cidade"] == cidade) & (passadas["h"] == h)
                     & (passadas["data_alvo"] >= inicio) & (passadas["data_alvo"] <= fim)]
        fig.add_trace(go.Scatter(x=p["data_alvo"], y=p["previsto"], mode=modo,
                                 name=f"Previsão passada ({h} sem. antes)",
                                 line=dict(color="#d9534f", dash="dot"), marker=dict(size=4),
                                 hovertemplate=FORMATO_DATA_HOVER + "<extra>Previsão passada</extra>"))
        p = p.dropna(subset=["tend_real", "tend_prev"])
        if not p.empty:
            _faixas_tendencia(fig, p)

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

    fig.update_xaxes(tickformat="%m/%Y")
    fig.update_xaxes(title="Casos por semana epidemiológica (data de início)", row=2, col=1)
    if p.empty:
        fig.update_yaxes(visible=False, row=2, col=1)
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=10, b=0), barmode="overlay",
                      legend=dict(orientation="h", yanchor="top", y=-0.2))
    grafico(fig)
    if not p.empty:
        _resumo_acerto(p, h, recorte)
    fim_passadas = ""
    if passadas is not None and (passadas["cidade"] == cidade).any():
        ultima_passada = passadas.loc[passadas["cidade"] == cidade, "data_alvo"].max()
        fim_passadas = (f" Ela vai só até {ultima_passada:%d/%m/%Y}: as {SEMANAS_INSTAVEIS} semanas mais recentes dos "
                        "dados ficam de fora porque o InfoDengue ainda pode revisar os casos delas (as notificações "
                        "chegam com atraso), e comparar a previsão com um número que ainda vai mudar não mediria o "
                        "acerto de forma confiável. Pelo mesmo motivo, essas semanas também não entram no treino. O "
                        "mesmo corte vale para as faixas de tendência.")
    st.caption("Previsão passada: o que o modelo teria previsto na época, sem conhecer o futuro (retreinado a cada "
               f"mês só com os dados disponíveis até então).{fim_passadas} Detalhes e acerto por município em "
               "\"Detalhes do Modelo\".")
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
