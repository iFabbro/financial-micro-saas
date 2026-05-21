from __future__ import annotations

import asyncio
import json
import sqlite3

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DB_PATH = 'db/financial_data.db'


def asset_exists(ticker: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("SELECT 1 FROM assets WHERE ticker = ? LIMIT 1", (ticker,))
        return cur.fetchone() is not None
    finally:
        conn.close()


async def main():
    server_params = StdioServerParameters(
        command='venv/bin/python',
        args=['src/mcp_server.py'],
    )

    print(f"[Client] Avvio server: {server_params.command} {' '.join(server_params.args)}")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as server:
            print("\n[Client] [1] Handshake (initialize)...")
            init_result = await server.initialize()
            print(f"[Client] OK: Server {init_result.serverInfo.name} inizializzato.")

            print("\n[Client] [2] List tools...")
            tools = await server.list_tools()
            print("[Client] OK: Tool disponibili ->", [t.name for t in tools.tools])

            print("\n[Client] [3] Call financial.initialize...")
            init_call = await server.call_tool("financial.initialize", {})
            if init_call.isError:
                print("[Client] Errore MCP (initialize):", init_call.content[0].text)
            else:
                print("[Client] OK:", init_call.content[0].text)

            print("\n[Client] [4] Call financial.add_asset (NVDA)...")
            if asset_exists("NVDA"):
                print("[Client] SKIP: NVDA già presente nel DB")
            else:
                asset_result = await server.call_tool(
                    "financial.add_asset",
                    {"ticker": "NVDA", "name": "NVIDIA Corp", "asset_class": "stock"},
                )
                if asset_result.isError:
                    print("[Client] Errore MCP (add_asset):", asset_result.content[0].text)
                else:
                    print("[Client] OK: Asset NVDA aggiunto")

            print("\n[Client] [5] Call financial.add_prices (NVDA)...")
            prices_result = await server.call_tool(
                "financial.add_prices",
                {
                    "ticker": "NVDA",
                    "prices": [
                        {"date": "2024-01-01", "close": 100.0},
                        {"date": "2024-01-02", "close": 101.0},
                        {"date": "2024-01-03", "close": 102.0},
                    ],
                },
            )
            if prices_result.isError:
                print("[Client] Errore MCP (add_prices):", prices_result.content[0].text)
            else:
                print("[Client] OK: Inseriti 3 prezzi per NVDA")

            print("\n[Client] [6] Call portfolio.optimize...")
            opt_result = await server.call_tool(
                "portfolio.optimize",
                {"ticker_list": ["NVDA"], "method": "ef"},
            )
            if opt_result.isError:
                print("[Client] Errore MCP (optimize):", opt_result.content[0].text)
            else:
                text = opt_result.content[0].text
                try:
                    data = json.loads(text)
                    print("[Client] OK: Pesi calcolati ->", data.get("weights"))
                    print("[Client] OK: Expected Return ->", data.get("expected_return"))
                except Exception:
                    print("[Client] OK:", text)

    print("\n[Client] Chiusura server...")


if __name__ == '__main__':
    asyncio.run(main())
