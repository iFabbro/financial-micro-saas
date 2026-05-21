SHELL := /bin/bash

.DEFAULT_GOAL := help

PYTHON := python3
PIP := $(PYTHON) -m pip

.PHONY: help install test reset-demo smoke demo run-server run-client run-report clean clean-release-bundle

help:
	@echo "Targets disponibili:"
	@echo "  make install              - installa dipendenze in editable mode"
	@echo "  make test                 - esegue pytest"
	@echo "  make reset-demo           - rigenera il seed demo"
	@echo "  make smoke                - esegue la smoke demo completa"
	@echo "  make demo                 - reset demo + smoke"
	@echo "  make run-server           - avvia il server MCP"
	@echo "  make run-client           - avvia il client"
	@echo "  make run-report           - stampa il report"
	@echo "  make clean                - pulizia file temporanei"
	@echo "  make clean-release-bundle  - pulizia output/release_bundle"

install:
	$(PIP) install -e .

test:
	$(PYTHON) -m pytest

reset-demo:
	$(PYTHON) scripts/seed_demo.py --reset

smoke:
	$(PYTHON) smoke_demo.py

demo: reset-demo smoke

run-server:
	$(PYTHON) src/mcp_server.py

run-client:
	$(PYTHON) src/client.py

run-report:
	$(PYTHON) src/report.py

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache

clean-release-bundle:
	bash scripts/clean_release_bundle.sh

