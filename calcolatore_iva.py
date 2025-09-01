import streamlit as st
import requests

def main():
    # Aliquote IVA Svizzera (2024)
    VAT_RATES = {
        "Standard (8.1%)": 0.081,
        "Essenziale (2.6%)": 0.026,
        "Alberghiero (3.8%)": 0.038
    }

    def get_exchange_rates():
        """Ottiene i tassi di cambio con base CHF (da API ECB)."""
        url = "https://api.exchangerate.host/latest?base=CHF"
        response = requests.get(url)
        #print(response.json()["success"])
        if response.status_code == 200 and response.json()["success"] != False:
            return response.json()["rates"]
        else:
            st.warning("Impossibile recuperare i tassi di cambio. Uso valori fissi di default.")
            return {"EUR": 0.95, "USD": 0.88, "CHF": 1.0}  # fallback valori

    def calcola_importo_con_iva(valore, valuta, categoria):
        rates = get_exchange_rates()

        # Conversione in CHF
        if valuta != "CHF":
            valore_chf = valore / rates.get(valuta, 1)
        else:
            valore_chf = valore

        # Calcolo IVA
        aliquota = VAT_RATES[categoria]
        iva = valore_chf * aliquota
        totale = valore_chf + iva

        return round(valore_chf, 2), round(iva, 2), round(totale, 2)

    # ------------------- Streamlit UI -------------------
    st.set_page_config(page_title="Calcolatore IVA Svizzera", page_icon="💰")

    st.title("🇨🇭 Calcolatore IVA Svizzera (Import/Export)")
    st.markdown("Inserisci i dati della merce per calcolare l'IVA in base alle aliquote svizzere.")

    # Input utente
    valore = st.number_input("Valore merce", min_value=0.0, value=1000.0, step=100.0)
    valuta = st.selectbox("Valuta", ["CHF", "EUR", "USD"])
    categoria = st.selectbox("Categoria prodotto (IVA)", list(VAT_RATES.keys()))

    # Calcolo
    if st.button("Calcola IVA"):
        netto_chf, iva, totale = calcola_importo_con_iva(valore, valuta, categoria)

        st.subheader("📊 Risultati")
        st.write(f"**Valore in CHF:** {netto_chf}")
        st.write(f"**IVA ({categoria}):** {iva}")
        st.write(f"**Totale con IVA:** {totale}")

        st.success("Calcolo completato ✅")


if __name__ == "__main__":
    main()