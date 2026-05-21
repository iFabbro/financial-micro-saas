#!/usr/bin/env python3
import asyncio
import datetime
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import aiosqlite

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.math_core import optimize_portfolio
from src.db_init import initialize_schema, get_db_connection

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("mcp_server")

DB_PATH = "./db/financial_data.db"
PROTOCOL_VERSION = "2024-11-05"


def jsonrpc_result(result: Any, request_id: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "result": result, "id": request_id}


def jsonrpc_error(code: int, message: str, request_id: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": request_id}


class MCPFinancialServer:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path


    async def mcp_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
            "capabilities": {
                "tools": {},
                "prompts": {},
                "resources": {}
            },
            "serverInfo": {
                "name": "financial-micro-saas-server",
                "version": "1.0.0"
            }
        }

    async def tool_initialize(self, **_params) -> Dict[str, Any]:
        """
        Applica lo schema operativo in modo idempotente.
        Delega a db_init.initialize_schema – unica fonte di verità per DDL.
        """
        await initialize_schema(self.db_path)
        logger.info("Database initialized")
        return {"status": "success", "message": "Database inizializzato correttamente."}

    async def tool_list_assets(self, **_params) -> List[Dict[str, Any]]:
        conn = await get_db_connection(self.db_path)
        try:
            cur = await conn.execute(
                "SELECT id, ticker, name, asset_class, created_at FROM assets ORDER BY ticker"
            )
            rows = await cur.fetchall()
        finally:
            await conn.close()
        return [dict(r) for r in rows]

    async def tool_add_asset(self, ticker: str, name: str, asset_class: str, **_params) -> Dict[str, Any]:
        if not ticker or not isinstance(ticker, str):
            raise ValueError("ticker must be a non-empty string")
        if not name or not isinstance(name, str):
            raise ValueError("name must be a non-empty string")
        if not asset_class or not isinstance(asset_class, str):
            raise ValueError("asset_class must be a non-empty string")

        conn = await get_db_connection(self.db_path)
        try:
            await conn.execute(
                "INSERT INTO assets (ticker, name, asset_class) VALUES (?, ?, ?)",
                (ticker, name, asset_class),
            )
            await conn.commit()
        finally:
            await conn.close()
        return {"status": "success", "ticker": ticker}

    async def tool_add_prices(self, ticker: str, prices: List[Dict[str, Any]], **_params) -> Dict[str, Any]:
        if not ticker or not isinstance(ticker, str):
            raise ValueError("ticker must be a non-empty string")
        if not isinstance(prices, list) or not prices:
            raise ValueError("prices must be a non-empty list")
            
        conn = await get_db_connection(self.db_path)
        try:
            
            cur = await conn.execute("SELECT id FROM assets WHERE ticker = ?", (ticker,))
            row = await cur.fetchone()
            if not row:
                raise ValueError(f"Asset with ticker '{ticker}' not found. Add it first.")
            asset_id = row["id"]
            
            insert_data = []
            for p in prices:
                if not isinstance(p, dict) or "date" not in p or "close" not in p:
                    raise ValueError("Each price entry must be an object with 'date' and 'close' fields")
                insert_data.append((
                    asset_id, p["date"], p.get("open"), p.get("high"), p.get("low"), p["close"], p.get("volume")
                ))
                
            await conn.executemany(
                "INSERT OR REPLACE INTO prices (asset_id, date, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                insert_data
            )
            await conn.commit()
            return {"status": "success", "inserted": len(insert_data), "ticker": ticker}
        finally:
            await conn.close()

    async def tool_optimize_portfolio(
        self,
        ticker_list: List[str],
        method: str = "ef",
        target_return: Optional[float] = None,
        tenant_id: str = "default",
        portfolio_id: str = "default",
        **_params,
    ) -> Dict[str, Any]:
        """Read real close prices from DB for each requested ticker, then optimise."""
        # Pay-per-use billing audit log (Rule 6: Moesif/x402 requirement)
        audit_entry = {
            "event": "billing_audit",
            "tenant_id": tenant_id,
            "portfolio_id": portfolio_id,
            "usage_type": "optimization",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
        }
        logger.info(json.dumps(audit_entry))

        if not isinstance(ticker_list, list) or not ticker_list:
            raise ValueError("ticker_list must be a non-empty list of strings")
        if not all(isinstance(t, str) for t in ticker_list):
            raise ValueError("All elements in ticker_list must be strings")
        if target_return is not None and not isinstance(target_return, (int, float)):
            raise ValueError("target_return must be a number if provided")

        ticker_prices: Dict[str, List[float]] = {}
        conn = await get_db_connection(self.db_path)
        try:
            for ticker in ticker_list:
                cur = await conn.execute(
                    "SELECT p.close FROM prices p "
                    "JOIN assets a ON a.id = p.asset_id "
                    "WHERE a.ticker = ? "
                    "ORDER BY p.date ASC",
                    (ticker,),
                )
                rows = await cur.fetchall()
                if not rows:
                    raise ValueError(
                        f"No price data found for ticker '{ticker}'. "
                        "Use financial.add_asset and insert prices first."
                    )
                ticker_prices[ticker] = [row["close"] for row in rows]
        finally:
            await conn.close()
        result = await optimize_portfolio(
            ticker_prices, method=method, target_return=target_return
        )
        result_dict = result.to_dict()

        # Persisti la run nella history table (audit/storico)
        run_conn = await get_db_connection(self.db_path)
        try:
            await run_conn.execute(
                """
                INSERT INTO optimize_runs
                    (tenant_id, portfolio_id, method, tickers, weights,
                     expected_return, volatility, sharpe_ratio, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'success')
                """,
                (
                    tenant_id,
                    portfolio_id,
                    method,
                    json.dumps(sorted(ticker_list)),
                    json.dumps(result_dict.get("weights", {})),
                    result_dict.get("expected_return"),
                    result_dict.get("volatility"),
                    result_dict.get("sharpe_ratio"),
                ),
            )
            await run_conn.commit()
        finally:
            await run_conn.close()

        return result_dict

    async def tools_list(self, **_params) -> Dict[str, Any]:
        """MCP tools/list – return all available tools."""
        return {
            "tools": [
                {
                    "name": "financial.initialize",
                    "description": "Initialize the database schema (idempotent). Call once before other tools.",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "financial.list_assets",
                    "description": "List all financial assets stored in the database.",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "financial.add_asset",
                    "description": "Add a new asset to the database.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Asset ticker, e.g. AAPL"},
                            "name": {"type": "string", "description": "Friendly name of the asset"},
                            "asset_class": {"type": "string", "description": "Asset class, e.g. stock, bond"},
                        },
                        "required": ["ticker", "name", "asset_class"],
                    },
                },
                {
                    "name": "financial.add_prices",
                    "description": "Add historical prices for a given asset ticker.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Asset ticker, e.g. AAPL"},
                            "prices": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "date": {"type": "string", "description": "YYYY-MM-DD"},
                                        "close": {"type": "number"},
                                        "open": {"type": "number"},
                                        "high": {"type": "number"},
                                        "low": {"type": "number"},
                                        "volume": {"type": "integer"}
                                    },
                                    "required": ["date", "close"]
                                },
                                "description": "List of daily price objects"
                            }
                        },
                        "required": ["ticker", "prices"]
                    }
                },
                {
                    "name": "portfolio.optimize",
                    "description": "Optimize a portfolio for a given list of ticker symbols.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ticker_list": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of tickers to include in the portfolio",
                            },
                            "method": {
                                "type": "string",
                                "description": "Optimization method (ef = efficient frontier)",
                                "default": "ef",
                            },
                            "target_return": {
                                "type": "number",
                                "description": "Optional annualised target return",
                            },
                            "tenant_id": {
                                "type": "string",
                                "description": "Tenant ID for billing (optional)"
                            },
                            "portfolio_id": {
                                "type": "string",
                                "description": "Portfolio ID for tracking (optional)"
                            }
                        },
                        "required": ["ticker_list"],
                    },
                },
            ]
        }

    async def tools_call(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        **_params
    ) -> Dict[str, Any]:
        """MCP tools/call – dispatch to the named tool implementation."""
        if arguments is None:
            arguments = {}
        tool_dispatch = {
            "financial.initialize": self.tool_initialize,
            "financial.list_assets": self.tool_list_assets,
            "financial.add_asset": self.tool_add_asset,
            "financial.add_prices": self.tool_add_prices,
            "portfolio.optimize": self.tool_optimize_portfolio,
        }
        handler = tool_dispatch.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        result = await handler(**arguments)
        return {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
        }

    async def handle_request(self, rpc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(rpc, dict):
            return None

        method = rpc.get("method")
        request_id = rpc.get("id")
        params = rpc.get("params") or {}

        if method != "notifications/initialized":
            logger.info("Received request: method=%s id=%s", method, request_id)

        if method == "notifications/initialized" or method.startswith("notifications/"):
            return None

        if method == "initialize":
            return jsonrpc_result(await self.mcp_initialize(params), request_id)

        dispatch = {
            "tools/list": self.tools_list,
            "tools/call": self.tools_call,
            "financial.initialize": self.tool_initialize,
            "financial.list_assets": self.tool_list_assets,
            "financial.add_asset": self.tool_add_asset,
            "financial.add_prices": self.tool_add_prices,
            "portfolio.optimize": self.tool_optimize_portfolio,
        }

        handler = dispatch.get(method)
        if handler is None:
            return jsonrpc_error(-32601, f"Method not found: {method}", request_id)

        try:
            result = await handler(**params)
            logger.info("Success: method=%s id=%s", method, request_id)
            return jsonrpc_result(result, request_id)
        except TypeError as e:
            logger.warning("TypeError in %s: %s", method, e)
            return jsonrpc_error(-32602, f"Invalid params: {e}", request_id)
        except Exception as e:
            logger.error("Error in %s: %s", method, e)
            return jsonrpc_error(-32000, str(e), request_id)

    async def run(self):
        loop = asyncio.get_running_loop()
        while True:
            raw = await loop.run_in_executor(None, sys.stdin.readline)
            if not raw:
                break

            raw = raw.strip()
            if not raw:
                continue

            try:
                rpc = json.loads(raw)
            except Exception:
                logger.warning("Ignoring non-JSON input")
                continue

            try:
                resp = await self.handle_request(rpc)
                if resp is not None:
                    print(json.dumps(resp, ensure_ascii=False))
                    sys.stdout.flush()
            except Exception as e:
                request_id = rpc.get("id") if isinstance(rpc, dict) else None
                print(json.dumps(jsonrpc_error(-32000, str(e), request_id)))
                sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(MCPFinancialServer().run())


async def run_server():
    server = MCPFinancialServer()
    await server.tool_initialize()
    print("financial-mcp-server ready", file=sys.stderr)


def main():
    asyncio.run(run_server())

if __name__ == "__main__":
    main()
