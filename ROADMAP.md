# ROADMAP

## P0 - Bloccanti

- [x] Definire il perimetro del prodotto vendibile.
- [x] Stabilire il target utente principale e il caso d’uso prioritario.
- [x] Congelare il comportamento della demo pubblica.
- [x] Verificare che installazione, test e demo siano sempre ripetibili.
- [x] Confermare che i dati demo, test e real restino separati.
- [x] Pulire gli artefatti di build e i file inutili dal bundle.

## P1 - Fondamentali

- [x] Completare e rifinire `README.md`.
- [x] Finalizzare `RELEASE_CHECKLIST.md`.
- [x] Scrivere `RELEASE_NOTES.md` o usare la note del tag.
- [ ] Rendere il Makefile il punto di ingresso principale.
- [ ] Aggiungere una guida rapida “start in 5 minuti”.
- [ ] Preparare uno script di reset ambiente se serve.
- [ ] Verificare logging, error handling e messaggi utente.

## P2 - Vendibilità

- [ ] Scrivere una proposta di valore in una riga.
- [ ] Preparare screenshot o una breve demo video.
- [ ] Creare una landing page minima.
- [ ] Definire pricing iniziale o modello di vendita.
- [ ] Preparare una pagina “features” semplice.
- [ ] Aggiungere una sezione “FAQ” con i dubbi tipici.
- [ ] Descrivere chiaramente i limiti della versione attuale.

## P3 - Raffinamento

- [ ] Valutare Docker o un bundle distributivo.
- [ ] Aggiungere metriche di uso e osservabilità.
- [ ] Migliorare la UX di report e dashboard.
- [ ] Ridurre il rumore nei log.
- [ ] Aggiungere versioning semantico più rigoroso.
- [ ] Automatizzare i controlli di release.

## P4 - Extra

- [ ] Valutare integrazioni future con altri connettori dati.
- [ ] Valutare esportazioni aggiuntive per report e audit.
- [ ] Valutare UI più avanzata per utenti non tecnici.
- [ ] Valutare feature premium da vendere in una versione successiva.

## Sequenza consigliata

1. Chiudi i P0.
2. Chiudi i P1.
3. Prepara packaging e materiali di vendita.
4. Lancia una release v0.1.0.
5. Raccogli feedback e fai una seconda iterazione.

## Criterio di vendita

Il progetto è “vendibile” quando un utente riesce a:

- capire subito cosa risolve;
- installarlo senza assistenza;
- lanciare la demo senza errori;
- vedere un output utile;
- fidarsi che i dati non siano contaminati;
- avere un’idea chiara di cosa compra.

## Stato attuale

- Demo end-to-end stabile.
- Test automatizzati verdi.
- Seed demo ripetibile.
- Makefile operativo.
- Documentazione in aggiornamento.
