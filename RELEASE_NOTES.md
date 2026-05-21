# Release v0.1.0

Data: 2026-05-21

## Highlights

- Aggiunto flusso demo end-to-end stabile con seed automatico e smoke demo.
- Introdotti server MCP, client, report e ottimizzazione portfolio.
- Separati i profili `real`, `demo` e `test` per ridurre contaminazioni tra ambienti.
- Aggiunto `Makefile` per i comandi operativi principali.
- Aggiunto `pytest.ini` per isolare la suite di test reale.

## Verifiche completate

- `make install`
- `make test`
- `make demo`
- `make clean`

## Note

- Il seed demo è idempotente e ripetibile.
- La smoke demo usa automaticamente il database demo.
- Il progetto è pronto per demo e rilascio base.
