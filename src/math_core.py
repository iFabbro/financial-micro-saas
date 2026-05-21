#!/usr/bin/env python
"""
Core matematico per ottimizzazione di portafogli.

Usa PyPortfolioOpt per:
- Ledoit‑Wolf shrinkage della matrice di covarianza
- Maximization di Sharpe Ratio
- Ritorno pesi e metriche di rischio.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from dataclasses import asdict

import asyncio
import pandas as pd
from pypfopt import EfficientFrontier, HRPOpt, risk_models, expected_returns
from pypfopt.exceptions import OptimizationError


@dataclass
class OptimizationResult:
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    # info aggiuntive opzionali
    additional_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


async def optimize_portfolio(
    ticker_prices: Dict[str, List[float]],
    target_return: Optional[float] = None,
    method: str = "ef",  # "ef" (Efficient Frontier) or "hrp" (Hierarchical Risk Parity)
) -> OptimizationResult:
    """
    Optimizza un portafoglio dati prezzi di chiusura per tickers.

    ticker_prices: dict(ticker -> list di 'close' a intervalli regolari, es. daily)
    """
    # 1. Costruisci un DataFrame con i ritorni giornalieri
    df = pd.DataFrame(ticker_prices)

    # 2. Ritorni giornalieri
    daily_returns = df.pct_change().dropna()

    # 3. Matrice di covarianza con Ledoit‑Wolf shrinkage
    mu = expected_returns.mean_historical_return(daily_returns, returns_data=True)
    S = risk_models.CovarianceShrinkage(
        daily_returns, returns_data=True
    ).ledoit_wolf()

    # 4. Tipo di ottimizzazione
    try:
        if method == "ef":
            ef = EfficientFrontier(mu, S)
            # se target_return è None, auto‑tune (max Sharpe)
            if target_return is not None:
                ef.efficient_return(target_return)
            else:
                # default: massimizza Sharpe
                ef.max_sharpe()
        elif method == "hrp":
            hrp = HRPOpt(daily_returns)
            # non usa mus/S esplicitamente
        else:
            raise ValueError(f"method not supported: {method}")

        if method == "ef":
            raw_weights = ef.clean_weights()
            expected_return, volatility, sharpe_ratio = ef.portfolio_performance()
        else:
            # HRPOpt
            hrp.optimize()
            raw_weights = hrp.clean_weights()
            expected_return, volatility, sharpe_ratio = hrp.portfolio_performance()

    except OptimizationError as e:
        raise RuntimeError(f"Portfolio optimization failed: {e}")

    # prepara il dict finito
    weights = {ticker: value for ticker, value in raw_weights.items() if value > 0.0001}

    return OptimizationResult(
        weights=weights,
        expected_return=float(expected_return),
        volatility=float(volatility),
        sharpe_ratio=float(sharpe_ratio),
    )


# NOTE: La lettura dei prezzi dal DB e il dispatch verso optimize_portfolio()
# avvengono in src/mcp_server.tool_optimize_portfolio().
# Questo modulo contiene solo logica matematica pura (nessun I/O).
