import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# Database connection
def init_db():
    conn = sqlite3.connect("partita_doppia.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS scritture (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT,
    tipo TEXT,
    conto_dare TEXT,
    conto_avere TEXT,
    importo REAL,
    descrizione TEXT
    )
    """)
    conn.commit()
    return conn


# Inserimento scritture multiple legate ad un'unica operazione
# conn → la connessione al database SQLite.
# data → la data della scrittura (es. 2025-08-25).
# tipo → il tipo di operazione scelta (es. “Acquisto estero”).
# righe → una lista di tuple (conto_dare, conto_avere, importo).
# descrizione → testo libero inserito dall’utente.
def registra_scrittura(conn, data, tipo, righe, descrizione=""):
    c = conn.cursor()
    # Il ciclo for itera su tutte le righe contabili collegate a quell’operazione.
    # Per esempio, per Spese doganali:
    # righe = [
    #       ("Spese doganali", "Debiti dogana", importo * 0.7),
    #       ("IVA a credito", "Debiti dogana", importo * 0.3)
    #  ]
    for conto_dare, conto_avere, importo in righe:
        c.execute(
            "INSERT INTO scritture (data, tipo, conto_dare, conto_avere, importo, descrizione) VALUES (?,?,?,?,?,?)",
            (data, tipo, conto_dare, conto_avere, importo, descrizione)
        )
    conn.commit()

def main():
    # --- Interfaccia Streamlit
    st.title("💼 Modulo Partita Doppia - Import/Export")

    # connessione db
    conn = init_db()

    st.sidebar.header("➕ Inserisci nuova scrittura")

    # selectbox
    tipo_operazione = st.sidebar.selectbox("Tipo di scrittura", [
    "Acquisto estero",
    "Pagamento fornitore estero",
    "Spese doganali",
    "Pagamento dazi/IVA dogana",
    "Vendita estero",
    "Pagamento cliente estero",
    "Sconto cliente estero",
    "Differenza cambio",
    "Trasporto internazionale",
    "Assicurazione merce",
    "Commissioni bancarie",
    "Interessi passivi"
    ])

    # input laterali
    data = st.sidebar.date_input("Data", datetime.today())
    importo = st.sidebar.number_input("Importo (CHF)", min_value=0.0, step=10.0)
    descrizione = st.sidebar.text_input("Descrizione")

    # click registrazione scrittura
    if st.sidebar.button("Registra"):
        righe = []
        if tipo_operazione == "Acquisto estero":
            righe = [("Merci", "Debiti fornitori esteri", importo)]
        elif tipo_operazione == "Pagamento fornitore estero":
            righe = [("Debiti fornitori esteri", "Banca", importo)]
        elif tipo_operazione == "Spese doganali":
            righe = [
            ("Spese doganali", "Debiti dogana", importo * 0.7),
            ("IVA a credito", "Debiti dogana", importo * 0.3)
            ]
        elif tipo_operazione == "Pagamento dazi/IVA dogana":
            righe = [("Debiti dogana", "Banca", importo)]
        elif tipo_operazione == "Vendita estero":
            righe = [("Crediti clienti esteri", "Ricavi export", importo)]
        elif tipo_operazione == "Pagamento cliente estero":
            righe = [("Banca", "Crediti clienti esteri", importo)]
        elif tipo_operazione == "Sconto cliente estero":
            righe = [("Sconti concessi", "Crediti clienti esteri", importo)]
        elif tipo_operazione == "Differenza cambio":
            scelta = st.sidebar.radio("Tipo", ["Utile su cambi", "Perdita su cambi"])
            if scelta == "Utile su cambi":
                righe = [("Banca", "Utile su cambi", importo)]
            else:
                righe = [("Perdita su cambi", "Banca", importo)]
        elif tipo_operazione == "Trasporto internazionale":
            righe = [("Spese trasporto", "Debiti trasportatore", importo)]
        elif tipo_operazione == "Assicurazione merce":
            righe = [("Spese assicurative", "Debiti assicurazione", importo)]
        elif tipo_operazione == "Commissioni bancarie":
            righe = [("Spese bancarie", "Banca", importo)]
        elif tipo_operazione == "Interessi passivi":
            righe = [("Interessi passivi", "Banca", importo)]

        #scrittura vera e propria
        if righe:
            registra_scrittura(conn, str(data), tipo_operazione, righe, descrizione)
            st.success(f"✅ Scrittura '{tipo_operazione}' registrata!")

    # Visualizzazione scritture raggruppate per operazione
    st.subheader("📊 Scritture registrate (raggruppate per operazione)")
    df_scritture = pd.read_sql_query("SELECT * FROM scritture ORDER BY id", conn)
    st.dataframe(df_scritture)

    # filtri
    if not df_scritture.empty:
        st.subheader("Filtri")

        # --- Filtro per tipologia ---
        tipi = df_scritture["tipo"].unique().tolist()
        tipo_sel = st.multiselect("Seleziona tipologia", tipi, default=tipi)

        # --- Filtro per data ---
        #Converto la colonna "data" in oggetti datetime.
        # Trovo la data minima e massima presenti nel DB.
        # Mostro un date picker con due campi (range di date).
        df_scritture["data"] = pd.to_datetime(df_scritture["data"])
        min_date = df_scritture["data"].min()
        max_date = df_scritture["data"].max()
        date_range = st.date_input("Intervallo date",
                                [min_date, max_date])

        # Applico i filtri
        df_filtrato = df_scritture[
            (df_scritture["tipo"].isin(tipo_sel)) &
            (df_scritture["data"].dt.date >= date_range[0]) &
            (df_scritture["data"].dt.date <= date_range[1])
        ]

        # --- Visualizzazione ---
        if df_filtrato.empty:
            st.warning("⚠️ Nessuna scrittura corrisponde ai filtri selezionati")
        else:
            for op, group in df_filtrato.groupby("tipo"):
                st.markdown(f"**Operazione:** {op}")
                st.table(group[["data","tipo","conto_dare","conto_avere","importo","descrizione"]])
    else:
        st.info("Nessuna scrittura presente nel database.")

    # Pulsante per svuotare il database (demo)
    st.subheader("⚠️ Azioni di manutenzione")
    if st.button("🗑️ Svuota database"):
        conn.execute("DELETE FROM scritture")
        conn.commit()
        st.warning("✅ Database svuotato!")


if __name__ == "__main__":
    main()