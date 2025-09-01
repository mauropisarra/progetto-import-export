import streamlit as st
from streamlit_option_menu import option_menu
import calcolatore_iva
import riconciliazione_doganale
import gestione_documentale
import dashboard_cambi
import partita_doppia
import fx_risk_app
import sys

print(sys.executable)

st.set_page_config(page_title="Hub Progetti Contabilità", page_icon="📂", layout="wide")

st.markdown("<h1 style='text-align: center;'>📂 Hub Progetti Contabilità</h1>", unsafe_allow_html=True)

selected = option_menu(
    menu_title=None,
    options=["Calcolatore IVA", "Riconciliazione Doganale", "Gestione Documentale",
              "Dashboard cambi e margini", "Partita doppia",
              "Analisi del rischio cambio per importazioni"],
    icons=["calculator", "table", "folder"],       # icone da bootstrap-icons
    menu_icon="cast",
    default_index=0,
    orientation="horizontal"
)

if selected == "Calcolatore IVA":
    calcolatore_iva.main()
elif selected == "Riconciliazione Doganale":
    riconciliazione_doganale.main()
elif selected == "Gestione Documentale":
    gestione_documentale.main()
elif selected == "Dashboard cambi e margini":
    dashboard_cambi.main()
elif selected == "Partita doppia":
    partita_doppia.main()
elif selected == "Analisi del rischio cambio per importazioni":
    fx_risk_app.main()