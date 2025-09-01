#Supporto multi-valuta → tutto convertito in CHF con tassi fissi.
#Evidenzia graficamente le discrepanze usando colori.
#Filtri per tipo di anomalia:
#   Solo fatture mancanti in dogana
#   Solo dogane mancanti in fatture
#   Solo discrepanze di valori

import streamlit as st
import pandas as pd

def main():
    st.set_page_config(page_title="Riconciliazione Doganale", page_icon="📑", layout="wide")

    st.title("📑 Riconciliazione Doganale - Import/Export")
    st.markdown("Carica i file contenenti **fatture** e **dichiarazioni doganali** per confrontare i dati.")

    # 2 Uploader file (csv o xls)
    col1, col2 = st.columns(2)

    with col1:
        file_fatture = st.file_uploader("📂 Carica file Fatture (Excel/CSV)", type=["csv", "xlsx"])

    with col2:
        file_dogane = st.file_uploader("📂 Carica file Dogane (Excel/CSV)", type=["csv", "xlsx"])

    # Tassi di cambio fissi
    EXCHANGE_RATES = {"CHF": 1.0, "EUR": 0.95, "USD": 0.88}

    # legge i file
    def load_file(file):
        if file is None:
            return None
        if file.name.endswith(".csv"):
            return pd.read_csv(file)
        else:
            return pd.read_excel(file)

    df_fatture = load_file(file_fatture)
    df_dogane = load_file(file_dogane)

    # Se entrambi i file sono caricati, mostra un’anteprima delle prime righe (head()) nella UI.
    if df_fatture is not None and df_dogane is not None:
        st.subheader("📋 Anteprima dati")
        st.write("**Fatture**")
        st.dataframe(df_fatture.head())
        st.write("**Dogane**")
        st.dataframe(df_dogane.head())

        # Normalizziamo colonne (esempio: "Numero fattura", "Valore", "Valuta")
        
        #Controlla che entrambi i file abbiano la colonna NumeroDocumento, che useremo per il confronto.
        #pd.merge() → unisce i due DataFrame sulla colonna NumeroDocumento.
        #suffixes → aggiunge _fattura e _dogana ai nomi delle colonne duplicate.
        #how="outer" → mantiene tutti i documenti anche se non hanno corrispondenza.
        #indicator=True → aggiunge una colonna _merge che indica se il documento è presente in entrambi o solo in uno dei due file
        
        if "NumeroDocumento" in df_fatture.columns and "NumeroDocumento" in df_dogane.columns:
            # Conversione valute in CHF
            # df_fatture.apply(...)
            # apply() applica una funzione a ogni riga del DataFrame.
            # lambda x: ... → funzione anonima che prende la riga x.
            # x["Valore"]/EXCHANGE_RATES.get(x["Valuta"],1)
            # Prende il valore originale della merce (x["Valore"]).
            # Divide per il tasso della valuta (x["Valuta"]) per convertirlo in CHF.
            # get(x["Valuta"],1) → se la valuta non è nel dizionario, usa 1 come default (nessuna conversione).
            # axis=1
            # Indica che la funzione viene applicata riga per riga e non per colonna.
            # Risultato
            # Viene creata una nuova colonna Valore_CHF sia in df_fatture sia in df_dogane.
            # Tutti i valori ora sono confrontabili direttamente in CHF.

            df_fatture["Valore_CHF"] = df_fatture.apply(lambda x: x["Valore"]/EXCHANGE_RATES.get(x["Valuta"],1), axis=1)
            df_dogane["Valore_CHF"] = df_dogane.apply(lambda x: x["Valore"]/EXCHANGE_RATES.get(x["Valuta"],1), axis=1)

            # merge
            # df_fatture → DataFrame delle fatture
            # df_dogane → DataFrame dei dati doganali
            # on="NumeroDocumento" → chiave comune su cui unire i due file.
            # Parametri principali
            # suffixes=("_fattura", "_dogana")
            #   Se ci sono colonne con lo stesso nome in entrambi i file (ad esempio Valore o Valuta), Pandas aggiunge il suffisso _fattura o _dogana per distinguerle.
            # how="outer"
            # Determina il tipo di merge:
            #   "inner" → conserva solo le righe che hanno la chiave in entrambi i file
            #   "left" → conserva tutte le righe di df_fatture, anche se non hanno corrispondenza in df_dogane
            #   "right" → conserva tutte le righe di df_dogane, anche se non hanno corrispondenza in df_fatture
            #   "outer" → conserva tutte le righe di entrambi i file → perfetto per riconciliazione perché vogliamo vedere anche i documenti mancanti
            #indicator=True
            #   Aggiunge una colonna _merge con valori:
            #   "both" → presente in entrambi i file
            #   "left_only" → presente solo in df_fatture
            #   "right_only" → presente solo in df_dogane

            merged = pd.merge(
                df_fatture,
                df_dogane,
                on="NumeroDocumento",
                suffixes=("_fattura", "_dogana"),
                how="outer",
                indicator=True
            )
            # Calcola la differenza tra il valore della fattura e quello dichiarato alla dogana.
            merged["Differenza_Valore"] = merged["Valore_fattura"].fillna(0) - merged["Valore_dogana"].fillna(0)

            st.subheader("📊 Risultati riconciliazione")

            # Colore rosso se discrepanza
            def highlight_discrepancy(row):
                if row["_merge"] != "both":
                    return ['background-color: yellow']*len(row)
                elif row["Differenza_Valore"] != 0:
                    return ['background-color: red']*len(row)
                else:
                    return ['background-color: lightgreen']*len(row)

            st.dataframe(merged.style.apply(highlight_discrepancy, axis=1))

            # Filtri
            #A seconda dell’opzione selezionata, si crea un DataFrame filtered con le righe corrispondenti.
            #"both" → presente in entrambi i file
            #"left_only" → presente solo nel primo DataFrame (df_fatture)
            #"right_only" → presente solo nel secondo DataFrame (df_dogane)
            #"Differenza_Valore" != 0 → evidenzia discrepanze nei valori.
            #Risultato
            #filtered contiene solo le righe rilevanti in base al filtro scelto.

            filtro = st.selectbox("Filtra anomalie", ["Tutte", "Solo discrepanze", "Solo fatture mancanti", "Solo dogane mancanti"])
            if filtro == "Solo discrepanze":
                filtered = merged[(merged["_merge"]=="both") & (merged["Differenza_Valore"] != 0)]
            elif filtro == "Solo fatture mancanti":
                filtered = merged[merged["_merge"]=="right_only"]
            elif filtro == "Solo dogane mancanti":
                filtered = merged[merged["_merge"]=="left_only"]
            else:
                filtered = merged
            st.subheader("📌 Anomalie filtrate")
            st.dataframe(filtered)
            
            # Esportazione Excel
            st.download_button(
                label="⬇️ Scarica risultati in Excel",
                data=merged.to_csv(index=False).encode("utf-8"),
                file_name="riconciliazione_doganale.csv",
                mime="text/csv"
            )
        else:
            st.warning("I file devono avere una colonna comune chiamata **NumeroDocumento**.")


if __name__ == "__main__":
    main()