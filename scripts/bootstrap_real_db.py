from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / 'db'
DB_DIR.mkdir(parents=True, exist_ok=True)
DB = DB_DIR / 'financial_real.db'

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date TEXT NOT NULL,
    close REAL NOT NULL,
    UNIQUE(ticker, date),
    FOREIGN KEY(ticker) REFERENCES assets(ticker)
);
CREATE TABLE IF NOT EXISTS optimization_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tenant_id TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    method TEXT NOT NULL,
    tickers TEXT NOT NULL,
    weights TEXT NOT NULL,
    expected_return REAL,
    volatility REAL,
    sharpe_ratio REAL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS static_portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

conn = sqlite3.connect(DB)
try:
    conn.executescript(SCHEMA)
    conn.commit()
finally:
    conn.close()

print(f'bootstrapped {DB}')