import streamlit as st
import pandas as pd
import datetime

def main():
    st.title("📦 Gestione Documentale Export")
    st.markdown("Carica, organizza e visualizza i documenti relativi all’export.")

    # Stato persistente (rimane tra interazioni)
    # st.session_state serve per salvare lo stato tra più interazioni (cioè se aggiorni la pagina non perdi i dati).
    # Se non esiste ancora la chiave "documenti", creo un DataFrame vuoto con tre colonne:
    # Nome File → nome del documento caricato
    # Tipo Documento → es. Fattura, Dogana, Certificato
    # Data Caricamento → data in cui l’utente lo ha caricato

    if "documenti" not in st.session_state:
        st.session_state.documenti = pd.DataFrame(columns=["Nome File", "Tipo Documento", "Data Caricamento"])

    # Caricamento multiplo
    uploaded_files = st.file_uploader(
        "📂 Carica i documenti (CSV, Excel, PDF, Immagini)",
        type=["csv", "xlsx", "pdf", "png", "jpg"],
        accept_multiple_files=True
    )

    tipo_documento = st.selectbox(
        "📑 Seleziona il tipo di documento",
        ["Fattura", "Dogana", "Certificato", "Altro"]
    )

    if uploaded_files and st.button("📥 Salva documenti"):
        nuovi_doc = []
        for file in uploaded_files:
            nuovi_doc.append({
                "Nome File": file.name,
                "Tipo Documento": tipo_documento,
                "Data Caricamento": datetime.date.today()
            })

        # Aggiungo al DataFrame esistente
        # pd.concat per aggiungere le nuove righe al DataFrame esistente in st.session_state.documenti.
        st.session_state.documenti = pd.concat(
            [st.session_state.documenti, pd.DataFrame(nuovi_doc)],
            ignore_index=True
        )
        st.success("✅ Documenti caricati e salvati con successo!")

    # 🔍 Filtro e ricerca

    st.subheader("🔍 Ricerca documenti")
    filtro_tipo = st.multiselect("Filtra per tipo", st.session_state.documenti["Tipo Documento"].unique())
    filtro_nome = st.text_input("Cerca per nome")

    # Creo una copia del DataFrame con i documenti.
    # Applico i filtri scelti (tipo e nome).
    # Mostro il risultato in tabella con st.dataframe.

    df_filtered = st.session_state.documenti.copy()

    if filtro_tipo:
        df_filtered = df_filtered[df_filtered["Tipo Documento"].isin(filtro_tipo)]
    if filtro_nome:
        df_filtered = df_filtered[df_filtered["Nome File"].str.contains(filtro_nome, case=False, na=False)]

    st.dataframe(df_filtered, use_container_width=True)

    # (Opzionale) download tabella
    # Se il DataFrame filtrato non è vuoto, lo trasformo in CSV.
    if not df_filtered.empty:
        csv = df_filtered.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Scarica registro", csv, "documenti_export.csv", "text/csv")

if __name__ == "__main__":
    main()