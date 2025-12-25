import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="AllevaGem ERP - Vincenzo Dell'Oste", layout="wide", page_icon="🐄")

# --- TITOLO E INTRODUZIONE ---
st.title("🐄 AllevaGem ERP: Cruscotto Azienda da Latte 4.0")
st.markdown("### Sviluppato da Vincenzo Dell'Oste")
st.markdown("""
**Benvenuto nel centro di controllo.** Qui integriamo i dati biologici della stalla con i parametri economici.
*Logica: Dati Sensori -> Analisi Salute -> Calcolo IOFC (Margine).*
""")

# --- SIDEBAR: PARAMETRI ECONOMICI (SCENARIO ANALYSIS) ---
st.sidebar.header("⚙️ Parametri di Mercato")
st.sidebar.markdown("Modifica i valori per vedere l'impatto sul bilancio.")

# Prezzi simulati adattati in Euro (logica basata su Source 63 e 66)
# Nota: manteniamo l'unità di misura "cwt" (quintale corto) per fedeltà alle formule originali, ma in valuta Euro.
price_milk_cwt = st.sidebar.number_input("Prezzo Latte (€/quintale corto)", value=19.50, step=0.5)
feed_cost_per_cow = st.sidebar.number_input("Costo Razione (€/capo/giorno)", value=5.90, step=0.1)

# Conversione prezzo latte in libbre (1 cwt = 100 lbs) per il calcolo unitario
price_milk_lb = price_milk_cwt / 100

# --- GENERAZIONE DATI SIMULATI (IL "LIVELLO SENSORI") ---
# Simuliamo una mandria di 50 capi con dati da pedometri e mungitrici
@st.cache_data
def get_herd_data():
    np.random.seed(42) # Per riproducibilità
    n_cows = 50
    ids = range(101, 101 + n_cows)
    
    # Giorni in lattazione (DIM) casuali tra 10 e 300
    dims = np.random.randint(10, 300, n_cows)
    
    # Produzione base (Curva di lattazione semplificata)
    yields = []
    health_status = []
    ruminations = []
    
    for dim in dims:
        # Modello semplice di Wood: Picco iniziale e declino
        base_yield = 85 * (dim ** 0.15) * np.exp(-0.003 * dim)
        
        # Introduciamo variabilità biologica
        noise = np.random.normal(0, 5)
        
        # Simulazione eventi sanitari (Source 34, 79)
        # 10% probabilità di problema sanitario
        health_roll = np.random.rand()
        if health_roll < 0.05:
            status = "Sospetta Mastite" # Calo produzione, conducibilità alta (simulata)
            actual_yield = base_yield * 0.7 + noise # -30% produzione
            rumination = np.random.randint(300, 400) # Ruminazione bassa
        elif health_roll < 0.10:
            status = "Allarme Estro" # Picco attività (Source 31)
            actual_yield = base_yield + noise
            rumination = np.random.randint(400, 500) # Ruminazione normale ma attività alta
        else:
            status = "Sana"
            actual_yield = base_yield + noise
            rumination = np.random.randint(450, 600) # Ruminazione ottimale
            
        yields.append(round(max(0, actual_yield), 1))
        health_status.append(status)
        ruminations.append(rumination)
        
    df = pd.DataFrame({
        "ID Vacca": ids,
        "Stato Salute": health_status,
        "DIM (Giorni)": dims,
        "Produzione (lbs)": yields,
        "Ruminazione (min/giorno)": ruminations
    })
    return df

df = get_herd_data()

# --- CALCOLO METRICHE ECONOMICHE (INTEGRAZIONE ERP) ---
# Calcolo IOFC per ogni vacca (Source 55, 67)
df["Ricavo Latte (€)"] = df["Produzione (lbs)"] * price_milk_lb
df["Costo Alim. (€)"] = feed_cost_per_cow
df["IOFC (€)"] = df["Ricavo Latte (€)"] - df["Costo Alim. (€)"]

# --- DASHBOARD KPI ---
st.divider()
col1, col2, col3, col4 = st.columns(4)

avg_iofc = df["IOFC (€)"].mean()
tot_prod = df["Produzione (lbs)"].sum()
sick_cows = df[df["Stato Salute"] == "Sospetta Mastite"].shape[0]
estrus_cows = df[df["Stato Salute"] == "Allarme Estro"].shape[0]

col1.metric("Media IOFC Mandria", f"€{avg_iofc:.2f}", delta_color="normal")
col2.metric("Produzione Totale (Oggi)", f"{int(tot_prod)} lbs")
col3.metric("Allarmi Sanitari", f"{sick_cows}", delta="-Alert", delta_color="inverse")
col4.metric("In Estro (Da Fecondare)", f"{estrus_cows}", delta="Action", delta_color="normal")

# --- SEZIONE 1: ANALISI BIOLOGICA E ALLARMI ---
st.subheader("📡 Monitoraggio Mandria & Allarmi IoT")

# Filtro per mostrare solo vacche con problemi
show_alerts_only = st.checkbox("Mostra solo vacche con allarmi attivi")

if show_alerts_only:
    display_df = df[df["Stato Salute"] != "Sana"]
else:
    display_df = df

# Funzione per evidenziare le righe critiche
def highlight_status(val):
    color = ''
    if val == 'Sospetta Mastite':
        color = 'background-color: #ffcccc' # Rosso chiaro
    elif val == 'Allarme Estro':
        color = 'background-color: #ccffcc' # Verde chiaro
    return color

# Visualizzazione tabella formattata
st.dataframe(
    display_df.style.map(highlight_status, subset=['Stato Salute'])
    .format({"Ricavo Latte (€)": "€{:.2f}", "IOFC (€)": "€{:.2f}", "Produzione (lbs)": "{:.1f}"}),
    use_container_width=True
)

st.info("💡 **Nota Operativa:** L'ERP blocca automaticamente il latte delle vacche segnate in 'Rosso' se viene inserito un trattamento farmacologico nel sistema.")

# --- SEZIONE 2: CURVA DI LATTAZIONE (VISUALIZZAZIONE DATI) ---
st.subheader("📈 Analisi Curva di Lattazione")
st.markdown("Visualizza la relazione tra giorni in lattazione (DIM) e produttività. I punti rossi indicano animali problematici (scostamento dalla curva ideale).")

chart = alt.Chart(df).mark_circle(size=60).encode(
    x='DIM (Giorni)',
    y='Produzione (lbs)',
    color=alt.Color('Stato Salute', scale=alt.Scale(domain=['Sana', 'Sospetta Mastite', 'Allarme Estro'], range=['steelblue', 'red', 'green'])),
    tooltip=['ID Vacca', 'Stato Salute', 'Produzione (lbs)', 'IOFC (€)']
).interactive()

st.altair_chart(chart, use_container_width=True)

# --- SEZIONE 3: IMPATTO ECONOMICO TOTALE ---
st.subheader("💰 Proiezione Economica Giornaliera")
daily_revenue = df["Ricavo Latte (€)"].sum()
daily_feed_cost = df["Costo Alim. (€)"].sum()
daily_margin = daily_revenue - daily_feed_cost

col_a, col_b, col_c = st.columns(3)
col_a.success(f"Ricavo Lordo Totale: €{daily_revenue:.2f}")
col_b.warning(f"Costo Alimentare Totale: €{daily_feed_cost:.2f}")
col_c.info(f"Margine Operativo (IOFC Totale): €{daily_margin:.2f}")

st.markdown("---")
st.caption("AllevaGem ERP Demo | Sviluppato da Vincenzo Dell'Oste")
