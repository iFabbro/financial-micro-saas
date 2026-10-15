# AGENTS.md - Regole Globali per il Progetto Financial Micro-SaaS

Questo file definisce le regole globali per tutti gli agenti che lavorano su questo progetto.
Deve essere rispettato in ogni azione, workflow e skill.

## 1. Ambiente e Dipendenze

- Tutti i file Python devono essere scritti per **Python 3.11+**.
- Le dipendenze principali del progetto sono:
  - `aiosqlite>=0.19.0`
  - `python-dotenv`
  - `PyPortfolioOpt>=1.5,<2.0`
  - `cvxpy>=1.3`
  - `numpy>=1.20`
  - `pandas>=2.0`
  - `pytest`
  - `pytest-asyncio`

- Ogni script deve salvare i file direttamente nella root del progetto o nelle sue sottocartelle (`src/`, `db/`, `tests/`, `.agents/`).

## 2. Database SQLite e Pragmas

- Ogni connessione SQLite deve eseguire immediatamente:
  ```python
  PRAGMA foreign_keys = ON
  PRAGMA journal_mode = WAL
  PRAGMA busy_timeout = 30000
  ```
  All'apertura della connessione.

- Tutte le operazioni I/O sui database devono usare `aiosqlite` con un async context manager pool.
- Gli accessi sincroni a `sqlite3` sono proibiti all'interno di funzioni asincrone.

## 3. Logging e Debug

- Tutti i file devono includere un logger configurato con livello `DEBUG` o `INFO`.
- I log devono includere timestamps e il nome del file/module.

## 4. Test e Validazione

- Le modifiche al database devono essere testate con `pytest` e `pytest-asyncio`.
- Ogni nuovo tool o endpoint deve avere un test che verifica:
  - esecuzione corretta
  - integrità delle transazioni
  - esecuzione senza errori di deadlock

## 5. File Paths e Permessi

- Tutti i path devono essere assoluti o relativi alla root del progetto.
- Nessun hardcode di path utente specifico (`~`).
- L'agente deve scrivere i file direttamente nella directory specificata senza richiedere conferma manuale.

## 6. Pay-per-Use (Monetizzazione)

- I chiamati a `portfolio.optimize` devono essere registrati tramite Moesif/x402 per la fatturazione Pay-per-use.
- Ogni chiamata deve includere:
  - `tenant_id`
  - `portfolio_id`
  - `usage_type` ("optimization")
  - `timestamp`

## 7. Sicurezza e Compliance

- Nessuna credenziale o API key deve essere inclusa nel codice.
- Tutte le API keys devono essere caricate da `./.env` tramite `python-dotenv`.
- Nessuna chiamata di test o debug deve esporre dati sensibili.
