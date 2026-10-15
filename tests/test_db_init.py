"""
Test dello schema operativo del database SQLite – Financial Micro-SaaS.

Tutti i test usano un DB temporaneo (tempfile) per essere isolati
dall'eventuale DB di produzione in ./db/.
"""

import os
import sqlite3
import sys
import tempfile

import aiosqlite
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db_init import get_db_connection, initialize_database, initialize_schema


def _tmp_db() -> str:
    """Crea un file temporaneo vuoto e ne restituisce il path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return path


# ── schema e tabelle ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_schema_creates_all_tables():
    """initialize_schema crea le 4 tabelle operative."""
    db = _tmp_db()
    try:
        await initialize_schema(db)

        conn = await aiosqlite.connect(db)
        conn.row_factory = aiosqlite.Row
        try:
            cur = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = {row["name"] for row in await cur.fetchall()}
        finally:
            await conn.close()

        assert {"assets", "prices", "portfolios", "portfolio_weights", "optimize_runs"} <= table_names
    finally:
        os.unlink(db)


@pytest.mark.asyncio
async def test_schema_idempotent():
    """initialize_schema è idempotente: chiamate ripetute non sollevano errori."""
    db = _tmp_db()
    try:
        await initialize_schema(db)
        await initialize_schema(db)  # seconda volta: nessuna eccezione
        await initialize_schema(db)  # terza volta
    finally:
        os.unlink(db)


@pytest.mark.asyncio
async def test_schema_creates_index_on_prices():
    """L'indice idx_prices_asset_date deve essere creato su prices(asset_id, date)."""
    db = _tmp_db()
    try:
        await initialize_schema(db)

        conn = await aiosqlite.connect(db)
        conn.row_factory = aiosqlite.Row
        try:
            cur = await conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND name='idx_prices_asset_date'"
            )
            row = await cur.fetchone()
        finally:
            await conn.close()

        assert row is not None, "Indice idx_prices_asset_date mancante su prices"
    finally:
        os.unlink(db)


# ── foreign keys e vincoli ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fk_portfolio_weights_rejects_bad_asset():
    """portfolio_weights deve rifiutare asset_id inesistente (FK attivo)."""
    db = _tmp_db()
    try:
        await initialize_schema(db)
        conn = await get_db_connection(db)
        try:
            await conn.execute(
                "INSERT INTO portfolios (name) VALUES (?)", ("Test Portfolio",)
            )
            await conn.commit()

            with pytest.raises(Exception, match="FOREIGN KEY constraint failed"):
                await conn.execute(
                    "INSERT INTO portfolio_weights (portfolio_id, asset_id, weight) "
                    "VALUES (1, 9999, 0.5)"
                )
                await conn.commit()
        finally:
            await conn.close()
    finally:
        os.unlink(db)


@pytest.mark.asyncio
async def test_fk_prices_rejects_bad_asset():
    """prices deve rifiutare asset_id inesistente (FK attivo)."""
    db = _tmp_db()
    try:
        await initialize_schema(db)
        conn = await get_db_connection(db)
        try:
            with pytest.raises(Exception, match="FOREIGN KEY constraint failed"):
                await conn.execute(
                    "INSERT INTO prices (asset_id, date, close) "
                    "VALUES (9999, '2024-01-01', 100.0)"
                )
                await conn.commit()
        finally:
            await conn.close()
    finally:
        os.unlink(db)


@pytest.mark.asyncio
async def test_prices_cascade_delete():
    """Cancellare un asset deve cancellare in cascade i suoi prezzi."""
    db = _tmp_db()
    try:
        await initialize_schema(db)
        conn = await get_db_connection(db)
        try:
            await conn.execute(
                "INSERT INTO assets (ticker, name, asset_class) "
                "VALUES ('AAPL', 'Apple', 'stock')"
            )
            await conn.commit()

            cur = await conn.execute("SELECT id FROM assets WHERE ticker='AAPL'")
            asset_id = (await cur.fetchone())["id"]

            await conn.execute(
                "INSERT INTO prices (asset_id, date, close) VALUES (?, '2024-01-01', 150.0)",
                (asset_id,),
            )
            await conn.commit()

            await conn.execute("DELETE FROM assets WHERE id=?", (asset_id,))
            await conn.commit()

            cur = await conn.execute(
                "SELECT COUNT(*) as n FROM prices WHERE asset_id=?", (asset_id,)
            )
            count = (await cur.fetchone())["n"]
        finally:
            await conn.close()

        assert count == 0, "Le righe di prices non sono state cancellate in cascade"
    finally:
        os.unlink(db)


@pytest.mark.asyncio
async def test_prices_unique_constraint():
    """prices(asset_id, date) deve essere UNIQUE."""
    db = _tmp_db()
    try:
        await initialize_schema(db)
        conn = await get_db_connection(db)
        try:
            await conn.execute(
                "INSERT INTO assets (ticker, name, asset_class) "
                "VALUES ('TSLA', 'Tesla', 'stock')"
            )
            await conn.commit()

            cur = await conn.execute("SELECT id FROM assets WHERE ticker='TSLA'")
            asset_id = (await cur.fetchone())["id"]

            await conn.execute(
                "INSERT INTO prices (asset_id, date, close) VALUES (?, '2024-01-01', 200.0)",
                (asset_id,),
            )
            await conn.commit()

            with pytest.raises(sqlite3.IntegrityError):  # UNIQUE constraint
                await conn.execute(
                    "INSERT INTO prices (asset_id, date, close) VALUES (?, '2024-01-01', 205.0)",
                    (asset_id,),
                )
                await conn.commit()
        finally:
            await conn.close()
    finally:
        os.unlink(db)


# ── compatibilità backward ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_initialize_database_alias():
    """initialize_database() è l'alias di initialize_schema per compatibilità."""
    db = _tmp_db()
    try:
        await initialize_database(db)

        conn = await aiosqlite.connect(db)
        conn.row_factory = aiosqlite.Row
        try:
            cur = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            names = {r["name"] for r in await cur.fetchall()}
        finally:
            await conn.close()

        assert "assets" in names
        assert "prices" in names
    finally:
        os.unlink(db)


# ── lookup coerente con portfolio.optimize ────────────────────────────────────

@pytest.mark.asyncio
async def test_price_lookup_by_ticker():
    """Il lookup usato da portfolio.optimize (JOIN assets+prices ORDER BY date) funziona."""
    db = _tmp_db()
    try:
        await initialize_schema(db)
        conn = await get_db_connection(db)
        try:
            await conn.execute(
                "INSERT INTO assets (ticker, name, asset_class) "
                "VALUES ('GOOG', 'Alphabet', 'stock')"
            )
            await conn.commit()

            cur = await conn.execute("SELECT id FROM assets WHERE ticker='GOOG'")
            asset_id = (await cur.fetchone())["id"]

            prices_to_insert = [
                (asset_id, f"2024-01-{d:02d}", 100.0 + d) for d in range(1, 11)
            ]
            await conn.executemany(
                "INSERT INTO prices (asset_id, date, close) VALUES (?, ?, ?)",
                prices_to_insert,
            )
            await conn.commit()

            cur = await conn.execute(
                "SELECT p.close FROM prices p "
                "JOIN assets a ON a.id = p.asset_id "
                "WHERE a.ticker = ? "
                "ORDER BY p.date ASC",
                ("GOOG",),
            )
            rows = await cur.fetchall()
            closes = [r["close"] for r in rows]
        finally:
            await conn.close()

        assert len(closes) == 10
        assert closes == sorted(closes), "I prezzi non sono ordinati per data"
        assert closes[0] == 101.0
        assert closes[-1] == 110.0
    finally:
        os.unlink(db)
