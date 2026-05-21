#!/usr/bin/env python3
"""
Report minimale per il backend Financial Micro-SaaS V1.

Fornisce un riepilogo testuale chiaro e leggibile dei dati presenti
nel database SQLite operativo (assets, prezzi, e ottimizzazioni salvate).
Utilizza pandas per la formattazione tabellare dei risultati.
"""

import sqlite3
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Errore: pandas non è installato. Esegui: pip install pandas")
    sys.exit(1)

DB_PATH = Path("./db/financial_data.db")


def generate_report():
    if not DB_PATH.exists():
        print(f"Errore: Database non trovato al percorso {DB_PATH}.")
        print("Assicurati di aver inizializzato il database (es. tramite il client MCP).")
        return

    # Usiamo una connessione read-only a sqlite3 sincrono per semplicità e velocità del report
    conn = sqlite3.connect(f"file:{DB_PATH.resolve()}?mode=ro", uri=True)

    print("\n" + "=" * 70)
    print(" FINANCIAL MICRO-SAAS - SYSTEM REPORT ".center(70))
    print("=" * 70)

    # 1. ASSETS
    print("\n--- 1. ASSET REGISTRATI ---")
    try:
        assets_df = pd.read_sql_query(
            "SELECT id, ticker, name, asset_class, created_at FROM assets ORDER BY id", 
            conn
        )
        if assets_df.empty:
            print("Nessun asset registrato nel database.")
        else:
            print(assets_df.to_string(index=False))
    except Exception as e:
        print(f"Errore durante la lettura degli asset: {e}")

    # 2. PRICES SUMMARY
    print("\n--- 2. RIEPILOGO PREZZI ---")
    try:
        query_prices = """
        SELECT 
            a.ticker, 
            COUNT(p.id) as total_days_loaded, 
            MIN(p.date) as first_date, 
            MAX(p.date) as last_date
        FROM assets a
        LEFT JOIN prices p ON a.id = p.asset_id
        GROUP BY a.id, a.ticker
        ORDER BY a.ticker
        """
        prices_df = pd.read_sql_query(query_prices, conn)
        if prices_df.empty:
            print("Nessun dato di prezzo trovato.")
        else:
            # Sostituisci None/NaN con stringhe leggibili per gli asset senza prezzi
            prices_df = prices_df.fillna("-")
            print(prices_df.to_string(index=False))
    except Exception as e:
        print(f"Errore durante la lettura dei prezzi: {e}")

    # 3. STORICO RUN DI OTTIMIZZAZIONE
    print("\n--- 3. STORICO RUN PORTFOLIO.OPTIMIZE ---")
    try:
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
        runs_df = pd.read_sql_query(query_runs, conn)
        if runs_df.empty:
            print("Nessuna run storicizzata.")
        else:
            print(runs_df.to_string(index=False))
    except Exception as e:
        print(f"Errore durante la lettura dello storico run: {e}")

    # 4. PORTAFOGLI STATICI SALVATI
    print("\n--- 4. PORTAFOGLI STATICI SALVATI ---")
    try:
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
        weights_df = pd.read_sql_query(query_portfolios, conn)
        if weights_df.empty:
            print("Nessun portafoglio statico salvato nel database.")
        else:
            print(weights_df.to_string(index=False))
    except Exception as e:
        print(f"Errore durante la lettura dei portafogli: {e}")

    print("\n" + "=" * 70 + "\n")
    conn.close()


if __name__ == "__main__":
    generate_report()


def main():
    generate_report()

if __name__ == "__main__":
    main()
