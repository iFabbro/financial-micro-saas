import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

# Configurazione base della pagina
st.set_page_config(
    page_title="Financial Micro-SaaS Dashboard", 
    page_icon="📈", 
    layout="wide"
)

DB_PATH = Path("./db/financial_data.db")

st.title("📈 Financial Micro-SaaS - System Dashboard")
st.markdown("Visualizzazione read-only dei dati e dello stato operativo del backend MCP.")

@st.cache_data(ttl=60)
def load_data(query: str) -> pd.DataFrame:
    """Legge dati in sola lettura dal database SQLite con cache di 60s."""
    if not DB_PATH.exists():
        return pd.DataFrame()
    # Apre in sola lettura per evitare lock e scritture accidentali
    with sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True) as conn:
        return pd.read_sql_query(query, conn)

if not DB_PATH.exists():
    st.error(f"Database non trovato al percorso `{DB_PATH}`. Esegui il client MCP per inizializzare il sistema.")
    st.stop()

# --- CARICAMENTO DATI ---
assets_df = load_data("SELECT id, ticker, name, asset_class, created_at FROM assets ORDER BY ticker")

query_prices = """
SELECT 
    a.ticker, 
    COUNT(p.id) as total_days_loaded, 
    MIN(p.date) as first_date, 
    MAX(p.date) as last_date
FROM assets a
LEFT JOIN prices p ON a.id = p.asset_id
GROUP BY a.id, a.ticker
ORDER BY total_days_loaded DESC, a.ticker
"""
prices_df = load_data(query_prices)

query_portfolios = """
SELECT 
    port.name as portfolio_name, 
    a.ticker, 
    pw.weight
FROM portfolios port
JOIN portfolio_weights pw ON port.id = pw.portfolio_id
JOIN assets a ON pw.asset_id = a.id
ORDER BY port.name, pw.weight DESC
"""
try:
    weights_df = load_data(query_portfolios)
except Exception:
    weights_df = pd.DataFrame()

query_runs = """
SELECT
    id,
    run_at,
    tenant_id,
    portfolio_id,
    method,
    tickers,
    weights,
    ROUND(expected_return, 4) as expected_return,
    ROUND(volatility, 4)      as volatility,
    ROUND(sharpe_ratio, 4)    as sharpe_ratio,
    status
FROM optimize_runs
ORDER BY run_at DESC
LIMIT 20
"""
try:
    runs_df = load_data(query_runs)
except Exception:
    runs_df = pd.DataFrame()

# --- METRICHE SINTETICHE ---
st.subheader("🎯 Sintesi Operativa")
tot_assets = len(assets_df) if not assets_df.empty else 0
tot_tickers_prices = len(prices_df[prices_df['total_days_loaded'] > 0]) if not prices_df.empty else 0
tot_prices = int(prices_df['total_days_loaded'].sum()) if not prices_df.empty else 0
tot_runs = len(runs_df) if not runs_df.empty else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Asset Registrati", tot_assets)
m2.metric("Ticker con Prezzi", tot_tickers_prices)
m3.metric("Prezzi Totali Caricati", tot_prices)
m4.metric("Run Ottimizzazione", tot_runs)

st.divider()

# --- TABELLE DETTAGLIO ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("🏦 Anagrafica Asset")
    if assets_df.empty:
        st.info("Nessun asset registrato.")
    else:
        st.dataframe(assets_df, use_container_width=True, hide_index=True)

with col2:
    st.subheader("📊 Copertura Storica Prezzi")
    if prices_df.empty:
        st.info("Nessun prezzo caricato.")
    else:
        # Evidenzia i ticker senza prezzi
        def highlight_no_prices(row):
            if row['total_days_loaded'] == 0:
                return ['background-color: rgba(255, 100, 100, 0.15)'] * len(row)
            return [''] * len(row)
            
        prices_df_clean = prices_df.fillna("-")
        st.dataframe(prices_df_clean.style.apply(highlight_no_prices, axis=1), use_container_width=True, hide_index=True)

st.divider()

st.subheader("💼 Portafogli Statici Salvati")
if weights_df.empty:
    st.info("Nessun portafoglio statico salvato nel database.")
else:
    st.dataframe(weights_df, use_container_width=True, hide_index=True)

st.divider()

st.subheader("🕐 Storico Run portfolio.optimize")
if runs_df.empty:
    st.info("Nessuna run storicizzata. Invoca `portfolio.optimize` via client MCP per registrare il primo evento.")
else:
    # Brief automatico: ultima run disponibile
    last = runs_df.iloc[0]
    st.markdown(
        f"**Ultima run:** `{last['run_at']}` &nbsp;|&nbsp; "
        f"Tickers: `{last['tickers']}` &nbsp;|&nbsp; "
        f"Method: `{last['method']}` &nbsp;|&nbsp; "
        f"Status: `{last['status']}` &nbsp;|&nbsp; "
        f"Sharpe: `{last['sharpe_ratio']}`"
    )
    st.dataframe(runs_df, use_container_width=True, hide_index=True)

st.divider()
st.caption("Financial Micro-SaaS V1 Backend - Phase 3 Dashboard")
