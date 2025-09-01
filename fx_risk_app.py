# fx_risk_app.py
"""
Analisi rischio cambio per importazioni - Streamlit app
- Upload CSV fatture in valuta estera
- Calcola esposizione (in base currency)
- Simula coperture (hedging) e scenari di mercato
- Visualizza esposizione per mese/trimestre e grafici di P&L
"""

from datetime import datetime
import io
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

def main():
    st.set_page_config(page_title="Rischio Cambio - Import", layout="wide")

    # -----------------------
    # Helper / Defaults
    # -----------------------
    SAMPLE_CSV = """invoice_id,date,currency,amount_foreign,fx_rate_at_booking,description
    INV-001,2025-01-15,USD,15000,0.92,macchinario
    INV-002,2025-02-10,USD,8000,0.94,componenti
    INV-003,2025-03-05,JPY,2000000,0.0069,materiale
    INV-004,2025-04-20,EUR,10000,1.0,spese
    """

    # converte la colonna date in formato datetime.
    def parse_dates(df, date_col="date"):
        df[date_col] = pd.to_datetime(df[date_col])
        return df

    # controlla che il CSV abbia le colonne minime (invoice_id, date, currency, amount_foreign)
    def ensure_columns(df):
        required = ["invoice_id", "date", "currency", "amount_foreign"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"CSV mancante colonne: {', '.join(missing)}")
        # if fx_rate_at_booking missing, we'll ask user for mapping or single rate
        return df

    # calcola il controvalore in valuta base (exposure_base) moltiplicando amount_foreign * fx_rate.
    # Se non c’è la colonna fx_rate_at_booking, chiede all’utente i tassi manuali.
    def add_base_amount(df, base_currency, fx_mapping):
        if "fx_rate_at_booking" in df.columns:
            df["fx_rate"] = df["fx_rate_at_booking"].astype(float)
        else:
            def map_rate(c):
                if c == base_currency:
                    return 1.0
                if c in fx_mapping:
                    return float(fx_mapping[c])
                raise KeyError(f"Manca tasso per valuta {c} e non è presente fx_rate_at_booking")
            df["fx_rate"] = df["currency"].map(map_rate)
        df["exposure_base"] = df["amount_foreign"].astype(float) * df["fx_rate"].astype(float)
        return df

    # aggrega l’esposizione per mese o trimestre.
    def group_exposure(df, freq="M"):
        # freq: 'M' month, 'Q' quarter
        df2 = df.copy()
        df2["period"] = df2["date"].dt.to_period(freq).dt.to_timestamp()
        g = df2.groupby("period", as_index=False).agg(
            exposure_foreign = ("amount_foreign", "sum"),
            exposure_base = ("exposure_base", "sum")
        ).sort_values("period")
        return g

    def simulate_shocks(df, hedge_pct, forward_rate_map, shock_percents, base_currency):
        """
        applica degli shock ai tassi di cambio (es. ±10%),
        calcola il P&L (profit/loss) con e senza copertura,
        ritorna una tabella con i risultati.
        """
        results = []
        for shock in shock_percents:
            # compute spot after shock
            df_tmp = df.copy()
            # spot = booking_rate * (1 + shock)
            df_tmp["spot_rate"] = df_tmp["fx_rate"] * (1 + shock)
            # hedge proportion
            h = hedge_pct / 100.0
            # forward rate per currency; default to booking rate if not provided
            def get_forward_rate(row):
                c = row["currency"]
                return forward_rate_map.get(c, row["fx_rate"])
            df_tmp["forward_rate"] = df_tmp.apply(get_forward_rate, axis=1)
            # P&L without hedge (base currency): (spot - booking) * amount_foreign
            df_tmp["pl_unhedged"] = (df_tmp["spot_rate"] - df_tmp["fx_rate"]) * df_tmp["amount_foreign"]
            # P&L if hedged proportion h at forward_rate:
            # Hedged portion: (forward_rate - booking)*amount_foreign (locked)
            # Unhedged portion: (spot_rate - booking)*amount_foreign
            df_tmp["pl_hedged"] = ((1 - h) * (df_tmp["spot_rate"] - df_tmp["fx_rate"]) + h * (df_tmp["forward_rate"] - df_tmp["fx_rate"])) * df_tmp["amount_foreign"]
            total_unhedged = df_tmp["pl_unhedged"].sum()
            total_hedged = df_tmp["pl_hedged"].sum()
            results.append({
                "shock_pct": shock,
                "total_pl_unhedged": total_unhedged,
                "total_pl_hedged": total_hedged,
                "delta_hedge": total_hedged - total_unhedged
            })
        return pd.DataFrame(results)

    # -----------------------
    # UI
    # -----------------------
    st.title("📦 Analisi rischio cambio per importazioni")
    st.markdown(
        """
        Carica un file CSV con le fatture in valuta estera e analizza l'esposizione cambi.
        Se non hai un file, usa il dataset d'esempio proposto.
        """
    )

    col1, col2 = st.columns([2,1])
    with col1:
        uploaded = st.file_uploader("Carica CSV fatture", type=["csv"], accept_multiple_files=False)
    with col2:
        if st.button("Scarica template CSV"):
            st.download_button("Download template", data=SAMPLE_CSV, file_name="template_fatture_fx.csv", mime="text/csv")

    # Dati reali (o CSV di esempio)
    if uploaded:
        try:
            df = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Errore lettura CSV: {e}")
            st.stop()
    else:
        st.info("Usando dataset di esempio.")
        df = pd.read_csv(io.StringIO(SAMPLE_CSV))

    # Validate & parse
    try:
        df = ensure_columns(df)
        df = parse_dates(df, "date")
    except Exception as e:
        st.error(str(e))
        st.stop()

    # Selezione valuta base
    base_currency = st.selectbox("Valuta base (reporting currency)", ["EUR","USD","GBP","JPY"], index=0)

    # If fx_rate_at_booking missing, ask for mapping
    missing_rates = "fx_rate_at_booking" not in df.columns
    st.write("---")
    st.header("Tassi di conversione")
    if not missing_rates:
        st.success("Il file contiene la colonna `fx_rate_at_booking` (tasso di conversione in valuta base al booking).")
    else:
        st.info("Inserisci i tassi di conversione (base per 1 unità foreign) per le valute presenti.")
        currencies = sorted(df['currency'].unique())
        fx_mapping = {}
        cols = st.columns(len(currencies))
        for i,c in enumerate(currencies):
            with cols[i]:
                if c == base_currency:
                    fx_mapping[c] = 1.0
                    st.text_input(f"{c} → {base_currency}", value="1.0", key=f"fx_{c}", disabled=True)
                else:
                    val = st.text_input(f"{c} → {base_currency}", value="", key=f"fx_{c}")
                    if val.strip() == "":
                        fx_mapping[c] = None
                    else:
                        try:
                            fx_mapping[c] = float(val)
                        except:
                            fx_mapping[c] = None
        # check missing
        if any(v is None for v in fx_mapping.values()):
            st.warning("Compila tutti i tassi per proseguire oppure aggiungi la colonna `fx_rate_at_booking` al CSV.")
            if st.button("Mostra preview dati (senza tassi completi)"):
                st.dataframe(df.head())
            st.stop()

    # Add base amounts
    try:
        if missing_rates:
            df = add_base_amount(df, base_currency, fx_mapping)
        else:
            df = add_base_amount(df, base_currency, {})
    except KeyError as e:
        st.error(str(e))
        st.stop()

    st.write("### Preview fatture")
    st.dataframe(df.head(20))

    # Aggregation choice
    st.write("---")
    st.header("Esposizione per periodo")
    agg_choice = st.radio("Aggregazione", ("Mensile", "Trimestrale"))
    freq = "M" if agg_choice == "Mensile" else "Q"
    grouped = group_exposure(df, freq=freq)

    fig1 = px.bar(grouped, x="period", y="exposure_base", labels={"period":"Periodo","exposure_base":f"Esposizione ({base_currency})"},
                title=f"Esposizione per {agg_choice.lower()} ({base_currency})")
    st.plotly_chart(fig1, use_container_width=True)

    st.write("Dati aggregati:")
    st.dataframe(grouped)

    # Hedging simulation controls
    st.write("---")
    st.header("Simulazione coperture (hedging)")
    colA, colB, colC = st.columns(3)
    with colA:
        hedge_pct = st.slider("Percentuale di copertura (%)", min_value=0, max_value=100, value=50, step=5)
    with colB:
        # For each currency ask forward rate
        st.write("Tasso forward per valuta (opzionale). Se vuoto -> usato tasso di booking.")
        currencies = sorted(df['currency'].unique())
        forward_rate_map = {}
        for c in currencies:
            if c == base_currency:
                forward_rate_map[c] = 1.0
            else:
                v = st.text_input(f"Forward {c}→{base_currency}", key=f"fw_{c}", value="")
                forward_rate_map[c] = float(v) if v.strip() != "" else None
    with colC:
        st.write("Scenari e simulazione")
        shocks_input = st.text_input("Shock % separati da virgola (es -0.1,0,0.1 per -10%/0/+10%)", value="-0.1,0,0.1")
        try:
            shocks = [float(s.strip()) for s in shocks_input.split(",") if s.strip() != ""]
        except:
            st.error("Formato shock non valido. Usa valori come -0.1,0,0.1")
            st.stop()
        montecarlo = st.checkbox("Usa Monte Carlo (1000 simulazioni) per distribuzione P&L", value=False)
        mc_sims = st.slider("Numero simulazioni MC", min_value=100, max_value=5000, value=1000, step=100)

    # Prepare forward_rate_map clean
    forward_rate_map_clean = {}
    for c,v in forward_rate_map.items():
        if v is None:
            # leave absent -> add later per-row default
            continue
        forward_rate_map_clean[c] = float(v)

    # Run shock simulation
    sim_df = simulate_shocks(df, hedge_pct, forward_rate_map_clean, shocks, base_currency)
    st.write("Risultati scenari shock:")
    st.dataframe(sim_df)

    # Plot P&L per scenario
    fig2 = px.line(sim_df.melt(id_vars="shock_pct", value_vars=["total_pl_unhedged","total_pl_hedged"],
                            var_name="serie", value_name="PL"),
                x="shock_pct", y="PL", color="serie",
                title="P&L totale per scenario (shock percentuale)")
    st.plotly_chart(fig2, use_container_width=True)

    # Monte Carlo (opzionale)
    """
    Attivabile con checkbox.
    Simula tanti scenari casuali di tassi di cambio basati su una volatilità annuale e un orizzonte temporale (giorni).
    Usa distribuzione normale per generare gli shock.
    Mostra:
        statistiche descrittive (media, deviazione standard, percentili),
        istogramma della distribuzione del P&L
    """
    if montecarlo:
        st.write("---")
        st.header("Monte Carlo: simulazione di scenari futuri (spot)")
        # We'll assume log-normal returns based on historical implied vol or user input
        vol = st.slider("Volatilità annuale implicita (%) usata per MC", min_value=5.0, max_value=60.0, value=12.0, step=0.5)
        horizon_days = st.number_input("Orizzonte (giorni)", value=90, min_value=1)
        vol_annual = vol / 100.0
        vol_period = vol_annual * np.sqrt(horizon_days / 252.0)
        st.write(f"Volatility for horizon ≈ {vol_period:.2%}")
        # For simplicity simulate shocks on overall portfolio by applying random shock to booking rates
        rng = np.random.default_rng(seed=42)
        shocks_mc = rng.normal(loc=0.0, scale=vol_period, size=mc_sims)
        # compute P&L arrays
        total_pl_unhedged = []
        total_pl_hedged = []
        for s in shocks_mc:
            res = simulate_shocks(df, hedge_pct, forward_rate_map_clean, [s], base_currency)
            total_pl_unhedged.append(res["total_pl_unhedged"].iloc[0])
            total_pl_hedged.append(res["total_pl_hedged"].iloc[0])
        mc_res = pd.DataFrame({
            "pl_unhedged": total_pl_unhedged,
            "pl_hedged": total_pl_hedged,
            "pl_diff": np.array(total_pl_hedged) - np.array(total_pl_unhedged)
        })
        st.write("Statistiche Monte Carlo (totale portafoglio):")
        st.write(mc_res.describe().T)
        # histogram
        fig_mc = px.histogram(mc_res.melt(value_vars=["pl_unhedged","pl_hedged"]), x="value", color="variable", barmode="overlay",
                            title="Distribuzione P&L Monte Carlo")
        st.plotly_chart(fig_mc, use_container_width=True)

    # KPI e sintesi
    """
    Mostra esposizione totale in valuta base.
    Calcola esposizione coperta (X%).
    Tabella con esposizione per valuta.
    Pulsante per scaricare un CSV con i dati arricchiti (exposure_base e fx_rate).
    """
    st.write("---")
    st.header("Sintesi e KPI")
    total_exposure = df["exposure_base"].sum()
    hedged_exposure = total_exposure * (hedge_pct/100.0)
    st.metric("Esposizione totale (base)", f"{total_exposure:,.2f} {base_currency}")
    st.metric("Esposizione coperta (valore teorico)", f"{hedged_exposure:,.2f} {base_currency}")

    # Show per-currency exposure table
    st.write("Esposizione per valuta:")
    per_ccy = df.groupby("currency").agg(amount_foreign_sum=("amount_foreign","sum"),
                                        exposure_base_sum=("exposure_base","sum")).reset_index()
    st.dataframe(per_ccy)

    # Allow user to download the computed dataset with exposures and rates
    out_buf = io.StringIO()
    df.to_csv(out_buf, index=False)
    st.download_button("Scarica dati fatture con esposizioni", data=out_buf.getvalue(), file_name="fatture_esposizioni.csv", mime="text/csv")

    st.write("---")
    st.info("Suggerimenti:\n- Aggiungi una colonna `fx_rate_at_booking` nel CSV per usare i tassi di booking reali.\n- Fornisci i tassi forward per simulare contratti chiusi al forward.\n- Estendi la logica per scadenze diverse (due date) e cashflow per mese se necessario.")

if __name__ == "__main__":
    main()