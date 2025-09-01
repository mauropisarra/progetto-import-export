# dashboard_cambi.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def main():
    st.title("💱 Dashboard Cambi & Margini Import-Export")

    # --- Input tassi di cambio
    st.sidebar.header("Tassi di cambio attuali")
    chf_eur = st.sidebar.number_input("CHF → EUR", value=0.95, step=0.01)
    chf_usd = st.sidebar.number_input("CHF → USD", value=1.10, step=0.01)

    # --- Input costi & ricavi
    st.sidebar.header("Dati aziendali")
    costo_import_eur = st.sidebar.number_input("Costo import (EUR)", value=50000, step=1000)
    ricavo_export_usd = st.sidebar.number_input("Ricavo export (USD)", value=80000, step=1000)

     # --- Slider per variazione cambio
    st.sidebar.header("📈 Scenario Planning")
    variazione = st.sidebar.slider("Variazione cambio (%)", min_value=-20, max_value=20, value=5, step=1)

    # --- Conversione in CHF
    costo_import_chf = costo_import_eur / chf_eur
    ricavo_export_chf = ricavo_export_usd / chf_usd
    margine = ricavo_export_chf - costo_import_chf

    # st.metric crea dei box con numeri evidenziati.
    st.subheader("📊 Risultati attuali")
    st.metric("Costo Import in CHF", f"{costo_import_chf:,.2f} CHF")
    st.metric("Ricavo Export in CHF", f"{ricavo_export_chf:,.2f} CHF")
    st.metric("Margine", f"{margine:,.2f} CHF")

    # --- Scenario dinamico
    st.subheader(f"🔮 Scenario con variazione ±{variazione}%")
    deltas = [-variazione/100, 0, variazione/100]
    scenari = []
    for delta in deltas:
        chf_eur_s = chf_eur * (1 + delta)
        chf_usd_s = chf_usd * (1 + delta)
        costo_s = costo_import_eur / chf_eur_s
        ricavo_s = ricavo_export_usd / chf_usd_s
        margine_s = ricavo_s - costo_s
        scenari.append({"Scenario": f"{int(delta*100)}%", "Margine CHF": margine_s})

    df_scenari = pd.DataFrame(scenari)
    st.dataframe(df_scenari)

    # --- Grafico scenari
    # Creiamo un grafico a barre con Scenario sull’asse X e Margine in CHF sull’asse Y.
    fig, ax = plt.subplots()
    ax.bar(df_scenari["Scenario"], df_scenari["Margine CHF"], color="skyblue")
    ax.set_ylabel("Margine (CHF)")
    ax.set_title("Impatto variazione cambio sul margine")
    st.pyplot(fig)

if __name__ == "__main__":
    main()