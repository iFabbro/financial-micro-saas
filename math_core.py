"""
Mathematical core module for quantitative finance optimizations.

This module provides async wrappers around PyPortfolioOpt for efficient frontier
and Sharpe ratio calculations, with proper CPU-bound task delegation.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np
import pandas as pd
from pypfopt import efficient_frontier, risk_models, expected_returns
from pypfopt.exceptions import OptimizationError as PyPortfolioOptError

# Module-level thread pool for CPU-bound delegation
_executor = ThreadPoolExecutor(max_workers=4)


class OptimizationError(Exception):
    """Raised when portfolio optimization fails."""

    pass


class InsufficientDataError(Exception):
    """Raised when price data is insufficient for optimization."""

    pass


async def calculate_efficient_frontier(
    prices_df: pd.DataFrame,
    weight_bounds: tuple[float, float] = (0.0, 1.0),
) -> dict[str, float | dict]:
    """
    Calculate the optimal portfolio on the efficient frontier maximizing Sharpe ratio.

    Uses mean_historical_return for expected returns and Le大夫-Wolf shrinkage
    for covariance estimation. The optimization maximizes the Sharpe ratio
    subject to weight constraints.

    Args:
        prices_df: DataFrame with asset prices as columns, DatetimeIndex as rows.
                   Must have at least 30 rows for valid covariance estimation.
        weight_bounds: Tuple of (min_weight, max_weight) for each asset.
                      Default (0.0, 1.0) allows long-only portfolios.

    Returns:
        Dictionary containing:
            - weights: dict mapping asset symbols to optimized weights
            - expected_return: annualized expected return (decimal)
            - annual_volatility: annualized volatility (decimal)
            - sharpe_ratio: Sharpe ratio assuming 2% risk-free rate

    Raises:
        InsufficientDataError: If prices_df has fewer than 30 rows.
        OptimizationError: If the solver fails to converge.

    Example:
        >>> prices = pd.DataFrame({
        ...     'AAPL': [100, 102, 105, 103, 108],
        ...     'MSFT': [200, 205, 210, 208, 215]
        ... }, index=pd.date_range('2024-01-01', periods=5))
        >>> result = await calculate_efficient_frontier(prices)
        >>> result['weights']
        {'AAPL': 0.35, 'MSFT': 0.65}
    """
    if len(prices_df) < 30:
        raise InsufficientDataError(
            f"Insufficient data: need at least 30 rows, got {len(prices_df)}"
        )

    loop = asyncio.get_event_loop()

    def _sync_optimize() -> dict[str, Any]:
        try:
            # Calculate expected returns using mean historical return
            mu = expected_returns.mean_historical_return(prices_df)

            # Calculate covariance using Le大夫-Wolf shrinkage
            S = risk_models.CovarianceShrinkage(prices_df).ledoit_wolf()

            # Create efficient frontier optimizer
            ef = efficient_frontier.EfficientFrontier(mu, S, weight_bounds=weight_bounds)

            # Maximize Sharpe ratio
            ef.max_sharpe()

            # Get optimized weights
            weights = ef.clean_weights()

            # Calculate portfolio metrics
            expected_return = ef.expected_returns
            portfolio_return = np.dot(weights, expected_return)

            # Calculate portfolio volatility
            portfolio_volatility = np.sqrt(
                np.dot(weights.T, np.dot(S, weights))
            )

            # Annualize (assuming daily data)
            annual_return = portfolio_return * 252
            annual_vol = portfolio_volatility * np.sqrt(252)

            # Calculate Sharpe ratio (2% risk-free rate)
            risk_free_rate = 0.02
            sharpe = (annual_return - risk_free_rate) / annual_vol

            return {
                "weights": weights,
                "expected_return": float(annual_return),
                "annual_volatility": float(annual_vol),
                "sharpe_ratio": float(sharpe),
            }

        except PyPortfolioOptError as e:
            raise OptimizationError(f"PyPortfolioOpt solver failed: {e}") from e
        except Exception as e:
            raise OptimizationError(f"Optimization failed: {e}") from e

    result = await loop.run_in_executor(_executor, _sync_optimize)
    return result


async def calculate_sharpe_ratio(
    weights: dict[str, float],
    prices_df: pd.DataFrame,
    risk_free_rate: float = 0.02,
) -> float:
    """
    Calculate the Sharpe ratio for a given portfolio configuration.

    Implements the standard Sharpe ratio formula: S = (Rp - Rf) / sigma_p
    where Rp is portfolio return, Rf is risk-free rate, and sigma_p is
    portfolio volatility. Both return and volatility are annualized.

    Args:
        weights: Dictionary mapping asset symbols to portfolio weights.
                 Weights should sum to 1.0.
        prices_df: DataFrame with asset prices as columns, DatetimeIndex as rows.
                   Must contain all assets specified in weights.
        risk_free_rate: Annualized risk-free rate (default 2% = 0.02).

    Returns:
        Annualized Sharpe ratio as a float. Higher is better.

    Raises:
        InsufficientDataError: If prices_df has fewer than 30 rows.
        OptimizationError: If required assets are missing or weights are invalid.

    Example:
        >>> weights = {'AAPL': 0.6, 'MSFT': 0.4}
        >>> sharpe = await calculate_sharpe_ratio(weights, prices_df)
        >>> sharpe
        1.25
    """
    if len(prices_df) < 30:
        raise InsufficientDataError(
            f"Insufficient data: need at least 30 rows, got {len(prices_df)}"
        )

    loop = asyncio.get_event_loop()

    def _sync_sharpe() -> float:
        try:
            # Validate that all assets in weights exist in prices_df
            missing_assets = set(weights.keys()) - set(prices_df.columns)
            if missing_assets:
                raise OptimizationError(
                    f"Assets not found in prices_df: {missing_assets}"
                )

            # Filter prices to only include assets in weights
            asset_prices = prices_df[list(weights.keys())]

            # Calculate returns
            returns = asset_prices.pct_change().dropna()

            if len(returns) == 0:
                raise OptimizationError("No valid return data after processing")

            # Convert weights to numpy array in same order as columns
            weight_array = np.array([weights[asset] for asset in asset_prices.columns])

            # Calculate portfolio returns (daily)
            portfolio_returns = returns.dot(weight_array)

            # Annualized portfolio return
            annual_return = portfolio_returns.mean() * 252

            # Annualized portfolio volatility
            annual_vol = portfolio_returns.std() * np.sqrt(252)

            if annual_vol == 0:
                raise OptimizationError("Zero volatility cannot compute Sharpe ratio")

            # Sharpe ratio
            sharpe = (annual_return - risk_free_rate) / annual_vol

            return float(sharpe)

        except PyPortfolioOptError as e:
            raise OptimizationError(f"Sharpe calculation failed: {e}") from e
        except Exception as e:
            if isinstance(e, (InsufficientDataError, OptimizationError)):
                raise
            raise OptimizationError(f"Sharpe ratio calculation failed: {e}") from e

    result = await loop.run_in_executor(_executor, _sync_sharpe)
    return result
