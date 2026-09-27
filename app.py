"""Painel do Dengue Insight (Streamlit): aviso de entrada e menu de navegação."""
import streamlit as st

from painel import detalhes, indicadores

AVISO = ("Este painel é resultado de um trabalho acadêmico (Projeto Integrador IV, UNIVESP). As previsões são "
         "experimentais e **não devem ser usadas como base para decisões oficiais de vigilância ou de saúde pública**.")
PALAVRA_ACEITE = "entendo"
# O aceite fica num cookie do navegador por 1 ano, para não perguntar a cada visita.
# A verificação é só no navegador (sem registro no servidor).
COOKIE_ACEITE = "dengue_insight_aviso"
VALIDADE_COOKIE = 365 * 24 * 3600

st.set_page_config(page_title="Dengue Insight | UNIVESP PI-IV", layout="wide")


def gravar_cookie():
    # O HTML roda num iframe da mesma origem, que pode gravar o cookie na página principal.
    # O conteúdo é fixo (não vem do usuário).
    with st.sidebar:
        st.iframe(f"<script>window.parent.document.cookie = "
                  f"'{COOKIE_ACEITE}=1; max-age={VALIDADE_COOKIE}; path=/; SameSite=Lax';</script>", height=1)


# ---------------------------------------------------------------- Aviso de entrada
aceito_cookie = st.context.cookies.get(COOKIE_ACEITE) == "1"
if not (aceito_cookie or st.session_state.get("aviso_aceito")):
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
if not aceito_cookie and not st.session_state.get("cookie_gravado"):
    gravar_cookie()
    st.session_state["cookie_gravado"] = True

# ---------------------------------------------------------------- Menu
paginas = st.navigation({"Seções": [
    st.Page(indicadores.pagina, title="Indicadores", icon=":material/monitoring:", url_path="indicadores",
            default=True),
    st.Page(detalhes.pagina, title="Detalhes do Modelo", icon=":material/insights:", url_path="detalhes"),
]})
st.sidebar.markdown("### 🦟 Dengue Insight")
st.sidebar.caption("Trabalho acadêmico (PI-IV, UNIVESP). Previsões experimentais, não usar para decisões oficiais.")
paginas.run()
