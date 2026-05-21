#!/usr/bin/env python3
"""
Modulo di inizializzazione del database SQLite – Financial Micro-SaaS.

Fonte di verità unica per lo schema operativo: tabelle, vincoli e indici.
Importato sia dal server MCP sia dai test.
"""

import asyncio
import logging
from pathlib import Path

import aiosqlite

# ── Configurazione ────────────────────────────────────────────────────────────

DB_PATH = Path("./db/financial_data.db")

logger = logging.getLogger("db_init")

# ── Schema DDL ────────────────────────────────────────────────────────────────
# Lista ordinata di statement DDL idempotenti (CREATE … IF NOT EXISTS).
# Modificare SOLO qui per evitare deriva tra server e modulo di init.

SCHEMA_DDL: list[str] = [
    # assets: anagrafica strumenti finanziari
    """
    CREATE TABLE IF NOT EXISTS assets (
        id          INTEGER PRIMARY KEY,
        ticker      TEXT    UNIQUE NOT NULL,
        name        TEXT,
        asset_class TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # prices: serie storica giornaliera per asset
    """
    CREATE TABLE IF NOT EXISTS prices (
        id       INTEGER PRIMARY KEY,
        asset_id INTEGER NOT NULL,
        date     DATE    NOT NULL,
        open     REAL,
        high     REAL,
        low      REAL,
        close    REAL    NOT NULL,
        volume   INTEGER,
        UNIQUE(asset_id, date),
        FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE
    )
    """,
    # indice su (asset_id, date) – ottimizza ORDER BY date e lookup per ticker
    "CREATE INDEX IF NOT EXISTS idx_prices_asset_date ON prices(asset_id, date)",
    # portfolios: metadati del portafoglio
    """
    CREATE TABLE IF NOT EXISTS portfolios (
        id          INTEGER PRIMARY KEY,
        name        TEXT NOT NULL,
        description TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # portfolio_weights: pesi ottimizzati per portafoglio+asset
    """
    CREATE TABLE IF NOT EXISTS portfolio_weights (
        id           INTEGER PRIMARY KEY,
        portfolio_id INTEGER NOT NULL,
        asset_id     INTEGER NOT NULL,
        weight       REAL    NOT NULL CHECK(weight >= 0 AND weight <= 1),
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(portfolio_id, asset_id),
        FOREIGN KEY(portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
        FOREIGN KEY(asset_id)     REFERENCES assets(id)     ON DELETE RESTRICT
    )
    """,
    # optimize_runs: storico delle run di portfolio.optimize (audit/history)
    """
    CREATE TABLE IF NOT EXISTS optimize_runs (
        id           INTEGER PRIMARY KEY,
        run_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        tenant_id    TEXT      NOT NULL DEFAULT 'default',
        portfolio_id TEXT      NOT NULL DEFAULT 'default',
        method       TEXT      NOT NULL DEFAULT 'ef',
        tickers      TEXT      NOT NULL,
        weights      TEXT      NOT NULL,
        expected_return REAL,
        volatility   REAL,
        sharpe_ratio REAL,
        status       TEXT      NOT NULL DEFAULT 'success'
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_optimize_runs_at ON optimize_runs(run_at DESC)",
]

# ── Helpers pubblici ──────────────────────────────────────────────────────────


async def initialize_schema(db_path: str | Path) -> None:
    """
    Applica SCHEMA_DDL su *db_path* in modo idempotente.

    Crea la directory padre se mancante.
    Apre una connessione dedicata, esegue tutti gli statement in una
    singola transazione e la chiude nel finally.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    try:
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA busy_timeout = 30000")
        for stmt in SCHEMA_DDL:
            await conn.execute(stmt)
        await conn.commit()
        logger.info("Schema applicato su %s", db_path)
    finally:
        await conn.close()


async def get_db_connection(db_path: str | Path = DB_PATH) -> aiosqlite.Connection:
    """
    Restituisce una connessione a SQLite con PRAGMA forzati e row_factory.
    Il chiamante è responsabile della chiusura.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(str(db_path))
    await conn.execute("PRAGMA foreign_keys = ON")
    await conn.execute("PRAGMA journal_mode = WAL")
    await conn.execute("PRAGMA busy_timeout = 30000")
    conn.row_factory = aiosqlite.Row
    return conn


async def initialize_database(db_path: str | Path = DB_PATH) -> None:
    """
    Alias pubblico di initialize_schema.
    Mantenuto per compatibilità con integratori esistenti.
    """
    await initialize_schema(db_path)


# ── Entrypoint CLI ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(initialize_schema(DB_PATH))
