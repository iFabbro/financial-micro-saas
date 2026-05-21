import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import aiosqlite
from src.mcp_server import MCPFinancialServer


# ── helpers ──────────────────────────────────────────────────────────────────

async def _seed_db(db_path: str, tickers: list[str], n_prices: int = 120) -> None:
    """Create schema and insert synthetic but DB-resident prices."""
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    try:
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")
        await conn.execute("PRAGMA busy_timeout = 30000")
        # schema
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS assets ("
            "  id INTEGER PRIMARY KEY,"
            "  ticker TEXT UNIQUE NOT NULL,"
            "  name TEXT, asset_class TEXT,"
            "  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        )
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS prices ("
            "  id INTEGER PRIMARY KEY,"
            "  asset_id INTEGER NOT NULL,"
            "  date DATE NOT NULL,"
            "  open REAL, high REAL, low REAL,"
            "  close REAL NOT NULL,"
            "  volume INTEGER,"
            "  UNIQUE(asset_id, date),"
            "  FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE)"
        )
        for i, ticker in enumerate(tickers):
            await conn.execute(
                "INSERT OR IGNORE INTO assets (ticker, name, asset_class) VALUES (?, ?, ?)",
                (ticker, ticker, "stock"),
            )
            cur = await conn.execute("SELECT id FROM assets WHERE ticker = ?", (ticker,))
            row = await cur.fetchone()
            asset_id = row["id"]
            base = 100.0 + i * 50
            for day in range(n_prices):
                date = f"2024-{(day // 30) + 1:02d}-{(day % 30) + 1:02d}"
                close = base + day * 0.5 + (day % 7) * 0.3
                await conn.execute(
                    "INSERT OR IGNORE INTO prices (asset_id, date, close) VALUES (?, ?, ?)",
                    (asset_id, date, close),
                )
        await conn.commit()
    finally:
        await conn.close()


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_initialize():
    server = MCPFinancialServer()
    request = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
        "id": "test-id-1",
    }
    response = await server.handle_request(request)

    assert response is not None
    assert response.get("jsonrpc") == "2.0"
    assert response.get("id") == "test-id-1"

    result = response.get("result")
    assert result is not None
    # MCP initialize response: capability negotiation only (no "status" field)
    assert result.get("protocolVersion") == "2024-11-05"
    assert "capabilities" in result
    assert "tools" in result["capabilities"]
    assert "serverInfo" in result
    assert result["serverInfo"].get("name") == "financial-micro-saas-server"


@pytest.mark.asyncio
async def test_mcp_tools_list():
    server = MCPFinancialServer()
    response = await server.handle_request(
        {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": "test-id-2"}
    )
    assert response is not None
    assert response.get("jsonrpc") == "2.0"
    assert response.get("id") == "test-id-2"

    result = response.get("result")
    assert result is not None
    assert "tools" in result
    tools = result["tools"]
    assert len(tools) == 5
    tool_names = [t["name"] for t in tools]
    assert "financial.initialize" in tool_names
    assert "financial.list_assets" in tool_names
    assert "financial.add_asset" in tool_names
    assert "financial.add_prices" in tool_names
    assert "portfolio.optimize" in tool_names


@pytest.mark.asyncio
async def test_portfolio_optimize_with_real_db_prices():
    """
    portfolio.optimize must read prices from the DB.
    Use a temp file DB so the test is fully isolated.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        tickers = ["AAPL", "MSFT"]
        await _seed_db(db_path, tickers, n_prices=120)

        server = MCPFinancialServer(db_path=db_path)
        # Applica schema completo (include optimize_runs introdotto in Fase 3)
        await server.tool_initialize()

        response = await server.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "portfolio.optimize",
                    "arguments": {"ticker_list": tickers, "method": "ef"},
                },
                "id": "test-id-3",
            }
        )

        assert response is not None
        assert response.get("jsonrpc") == "2.0"
        assert response.get("id") == "test-id-3"
        assert "error" not in response, f"Unexpected error: {response.get('error')}"

        call_result = response.get("result")
        assert call_result is not None
        content = call_result["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"

        payload = json.loads(content[0]["text"])
        assert "weights" in payload
        assert "expected_return" in payload
        assert "volatility" in payload
        assert "sharpe_ratio" in payload
        # weights must sum to ~1 (only non-zero weights are kept)
        total = sum(payload["weights"].values())
        assert abs(total - 1.0) < 0.01, f"Weights sum {total} != 1.0"

    finally:
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_portfolio_optimize_missing_ticker_returns_error():
    """portfolio.optimize must return a JSON-RPC error when a ticker has no prices."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        # seed only AAPL, then request AAPL + UNKNOWN
        await _seed_db(db_path, ["AAPL"], n_prices=60)
        server = MCPFinancialServer(db_path=db_path)

        response = await server.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "portfolio.optimize",
                    "arguments": {"ticker_list": ["AAPL", "UNKNOWN"], "method": "ef"},
                },
                "id": "test-id-4",
            }
        )

        assert response is not None
        assert "error" in response
        assert "UNKNOWN" in response["error"]["message"]

    finally:
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_tool_add_asset_validation():
    server = MCPFinancialServer()
    # Bad ticker
    with pytest.raises(ValueError, match="ticker must be a non-empty string"):
        await server.tool_add_asset(ticker="", name="Apple", asset_class="stock")
    with pytest.raises(ValueError, match="ticker must be a non-empty string"):
        await server.tool_add_asset(ticker=123, name="Apple", asset_class="stock")  # type: ignore

    # Bad name
    with pytest.raises(ValueError, match="name must be a non-empty string"):
        await server.tool_add_asset(ticker="AAPL", name="", asset_class="stock")
        
    # Bad asset_class
    with pytest.raises(ValueError, match="asset_class must be a non-empty string"):
        await server.tool_add_asset(ticker="AAPL", name="Apple", asset_class="")


@pytest.mark.asyncio
async def test_tool_add_prices_validation():
    server = MCPFinancialServer()
    
    # Bad ticker
    with pytest.raises(ValueError, match="ticker must be a non-empty string"):
        await server.tool_add_prices(ticker="", prices=[{"date": "2024-01-01", "close": 100.0}])
        
    # Bad prices list
    with pytest.raises(ValueError, match="prices must be a non-empty list"):
        await server.tool_add_prices(ticker="AAPL", prices=[])
    with pytest.raises(ValueError, match="prices must be a non-empty list"):
        await server.tool_add_prices(ticker="AAPL", prices=None) # type: ignore


@pytest.mark.asyncio
async def test_tool_optimize_portfolio_validation():
    server = MCPFinancialServer()
    
    # Bad ticker list
    with pytest.raises(ValueError, match="ticker_list must be a non-empty list"):
        await server.tool_optimize_portfolio(ticker_list=[])
    with pytest.raises(ValueError, match="ticker_list must be a non-empty list"):
        await server.tool_optimize_portfolio(ticker_list=None) # type: ignore
        
    # Bad elements
    with pytest.raises(ValueError, match="All elements in ticker_list must be strings"):
        await server.tool_optimize_portfolio(ticker_list=["AAPL", 123]) # type: ignore
        
    # Bad target return
    with pytest.raises(ValueError, match="target_return must be a number if provided"):
        await server.tool_optimize_portfolio(ticker_list=["AAPL"], target_return="high") # type: ignore


@pytest.mark.asyncio
async def test_financial_add_prices_success():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        server = MCPFinancialServer(db_path=db_path)
        
        # Initialize schema
        await server.tool_initialize()
        
        # Adding prices for non-existent asset fails
        with pytest.raises(ValueError, match="not found. Add it first"):
            await server.tool_add_prices(ticker="AAPL", prices=[{"date": "2024-01-01", "close": 150.0}])
            
        # Add asset
        await server.tool_add_asset(ticker="AAPL", name="Apple", asset_class="stock")
        
        # Missing required fields in price data
        with pytest.raises(ValueError, match="must be an object with 'date' and 'close' fields"):
            await server.tool_add_prices(ticker="AAPL", prices=[{"date": "2024-01-01"}])
            
        # Success addition
        res = await server.tool_add_prices(
            ticker="AAPL", 
            prices=[
                {"date": "2024-01-01", "close": 150.0, "open": 149.0},
                {"date": "2024-01-02", "close": 152.0}
            ]
        )
        assert res["status"] == "success"
        assert res["inserted"] == 2
    finally:
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_optimize_run_is_persisted():
    """
    Fase 3 – Ogni run di portfolio.optimize deve essere storicizzata
    nella tabella optimize_runs con i campi minimi corretti.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        tickers = ["AAPL", "MSFT"]
        await _seed_db(db_path, tickers, n_prices=120)

        server = MCPFinancialServer(db_path=db_path)
        # initialize_schema crea anche optimize_runs
        await server.tool_initialize()

        # Prima run
        response = await server.handle_request({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "portfolio.optimize",
                "arguments": {"ticker_list": tickers, "method": "ef",
                              "tenant_id": "test-tenant", "portfolio_id": "p1"},
            },
            "id": "run-test-1",
        })
        assert "error" not in response, f"Unexpected error: {response.get('error')}"

        # Verifica persistenza in optimize_runs
        conn = await aiosqlite.connect(db_path)
        conn.row_factory = aiosqlite.Row
        try:
            cur = await conn.execute("SELECT * FROM optimize_runs ORDER BY run_at DESC LIMIT 1")
            row = await cur.fetchone()
        finally:
            await conn.close()

        assert row is not None, "Nessuna run storicizzata dopo optimize"
        assert row["status"] == "success"
        assert row["method"] == "ef"
        assert row["tenant_id"] == "test-tenant"
        assert row["portfolio_id"] == "p1"
        assert "AAPL" in row["tickers"]
        assert "MSFT" in row["tickers"]
        assert row["expected_return"] is not None
        assert row["sharpe_ratio"] is not None
        # I pesi storicizzati devono sommare a ~1.0
        weights = json.loads(row["weights"])
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"Weights sum {total} != 1.0"

    finally:
        os.unlink(db_path)
