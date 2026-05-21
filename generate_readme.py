from pathlib import Path

ROOT = Path(__file__).resolve().parent
README = ROOT / "README.md"

content = """# Financial Micro SaaS

Financial Micro SaaS is a local MCP-based financial system for portfolio analysis, asset and price management, optimization, reporting, and a lightweight Streamlit dashboard.

## What it does

- Stores assets and historical prices in SQLite.
- Optimizes portfolios from stored market data.
- Exposes MCP tools for initialization, asset management, price ingestion, and optimization.
- Provides a read-only CLI report and a Streamlit dashboard.
- Persists run history and audit-friendly logs.

## Why it matters

This project is designed as a practical, installable local tool for portfolio workflows, internal demos, and agentic automation. It gives you a real backend, a simple client, and a visible dashboard without needing external infrastructure.

## Requirements

- Python 3.13+
- macOS or Linux
- pip

## Installation

```bash
python3 -m pip install -e .
```

## Quickstart

1. Install the package.
2. Start the MCP server.
3. Initialize the database schema.
4. Add assets and prices.
5. Run portfolio optimization.
6. Review the report or dashboard.

## Start the server

```bash
financial-mcp-server
```

## Run tests

```bash
python3 -m pytest -q
```

## Dashboard

```bash
streamlit run src/dashboard.py
```

## Demo flow

A good demo sequence is:

1. Start the server.
2. Initialize the database.
3. Add a few assets.
4. Upload price history.
5. Optimize a portfolio.
6. Open the dashboard and inspect the result.

## Main components

- `src/mcp_server.py`: MCP server and tool routing.
- `src/db_init.py`: centralized SQLite schema.
- `src/math_core.py`: portfolio optimization core.
- `src/client.py`: minimal end-to-end client.
- `src/report.py`: read-only report CLI.
- `src/dashboard.py`: Streamlit dashboard.

## Current status

- Installable package.
- Server command working.
- Test suite passing.
- Dashboard available.

## Suggested use cases

- Internal portfolio analysis.
- Advisor or analyst demo environment.
- Local agentic finance workflow.
- Lightweight mission-control dashboard for allocations and optimization runs.

## Notes

This project is intentionally local-first and easy to inspect. It is meant to be a solid MVP foundation that can be refined into a distributable product.
"""

README.write_text(content.strip() + "\n", encoding="utf-8")
print(README)
