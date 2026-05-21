from pathlib import Path
import sqlite3
import argparse

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "db" / "financial_demo.db"

ASSETS = [
    ("AAPL", "Apple Inc.", "EQUITY"),
    ("MSFT", "Microsoft", "EQUITY"),
    ("NVDA", "NVIDIA Corp", "EQUITY"),
    ("SPY", "SPDR S&P 500 ETF Trust", "ETF"),
]

PRICES = {
    "AAPL": [
        ("2024-01-01", 185.64),
        ("2024-01-02", 186.12),
        ("2024-01-03", 184.91),
        ("2024-01-04", 187.33),
        ("2024-01-05", 188.02),
    ],
    "MSFT": [
        ("2024-01-01", 374.66),
        ("2024-01-02", 376.20),
        ("2024-01-03", 375.11),
        ("2024-01-04", 378.44),
        ("2024-01-05", 379.08),
    ],
    "NVDA": [
        ("2024-01-01", 481.68),
        ("2024-01-02", 484.22),
        ("2024-01-03", 489.51),
        ("2024-01-04", 492.03),
        ("2024-01-05", 495.77),
    ],
    "SPY": [
        ("2024-01-01", 473.21),
        ("2024-01-02", 474.02),
        ("2024-01-03", 475.33),
        ("2024-01-04", 476.11),
        ("2024-01-05", 477.48),
    ],
}

def ensure_schema(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS asset_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        price_date TEXT NOT NULL,
        close_price REAL NOT NULL,
        UNIQUE(asset_id, price_date),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    );

    CREATE TABLE IF NOT EXISTS portfolio_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_at TEXT DEFAULT CURRENT_TIMESTAMP,
        tenant_id TEXT DEFAULT 'default',
        portfolio_id TEXT DEFAULT 'default',
        method TEXT,
        tickers TEXT,
        weights TEXT,
        expected_return REAL,
        volatility REAL,
        sharpe_ratio REAL,
        status TEXT
    );

    CREATE TABLE IF NOT EXISTS static_portfolios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        payload TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

def get_asset_id(conn, ticker):
    row = conn.execute("SELECT id FROM assets WHERE ticker=?", (ticker,)).fetchone()
    return row[0] if row else None

def main(reset=False):
    if reset and DB_PATH.exists():
        DB_PATH.unlink()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    ensure_schema(conn)

    if reset:
        for tbl in ["asset_prices", "portfolio_runs", "static_portfolios", "assets"]:
            conn.execute(f"DELETE FROM {tbl}")

    for ticker, name, asset_class in ASSETS:
        conn.execute(
            """
            INSERT INTO assets (ticker, name, asset_class)
            VALUES (?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name=excluded.name,
                asset_class=excluded.asset_class
            """,
            (ticker, name, asset_class),
        )

    for ticker, rows in PRICES.items():
        asset_id = get_asset_id(conn, ticker)
        if asset_id is None:
            raise RuntimeError(f"Asset mancante: {ticker}")
        conn.execute("DELETE FROM asset_prices WHERE asset_id=?", (asset_id,))
        conn.executemany(
            """
            INSERT INTO asset_prices (asset_id, price_date, close_price)
            VALUES (?, ?, ?)
            """,
            [(asset_id, d, p) for d, p in rows],
        )

    conn.commit()
    conn.close()
    print(f"seed demo applied -> {DB_PATH}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    main(reset=args.reset)