# Release Checklist

## Rilascio tecnico

- [x] `make install` funziona.
- [x] `make test` passa con la suite completa.
- [x] `make demo` esegue seed + smoke demo senza errori.
- [x] `make clean` rimuove cache e artefatti temporanei.
- [x] `pytest.ini` limita la discovery ai test reali.
- [x] `scripts/seed_demo.py --reset` crea un seed demo stabile e ripetibile.
- [x] `smoke_demo.py` usa automaticamente `financial_demo.db`.
- [x] Il server MCP risponde correttamente ai tool principali.
- [x] Il report finale viene generato correttamente.
- [x] Il dashboard headless si avvia senza errori.
- [x] I database `real`, `demo` e `test` restano separati.
- [x] Non ci sono copie di test che interferiscono con `pytest`.

## Dati e database

- [x] `financial_real.db` esiste ed è il DB sorgente.
- [x] `financial_demo.db` viene rigenerato da seed stabile.
- [x] `financial_test.db` è isolato per i test.
- [x] Il seed demo è idempotente.
- [x] Gli asset demo sono coerenti.
- [x] I prezzi demo sono coerenti.

## Qualità e test

- [x] La suite `pytest` passa con 18 test.
- [x] Non ci sono errori di import dovuti a duplicati in `output/release_bundle`.
- [x] `__pycache__` e `.pytest_cache` possono essere puliti con `make clean`.
- [x] Le smoke demo sono ripetibili.

## Operatività

- [ ] Aggiornare `README.md` con i comandi operativi principali.
- [ ] Aggiungere una breve nota sui profili `real`, `demo` e `test`.
- [ ] Verificare se il `Makefile` va reso self-documenting con `help` automatico.
- [ ] Preparare una release note breve per il tag finale.
- [ ] Decidere se includere un target `release` o `bundle` per il packaging.
- [ ] Fare una pulizia finale di eventuali file di debug o backup non necessari.

## Note finali

- [ ] Verificare che il bundle finale non includa artefatti inutili.
- [ ] Confermare che il progetto sia pronto per demo e rilascio.