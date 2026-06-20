"""Synthetic market regimes for stress-testing DCA vs God Buy the Dip.

The historical finding (DCA beats perfect-foresight dip-buying) hinges on the
market's long-term *upward drift*. To show that, we generate synthetic monthly
real-total-return paths over the *same* dates as the historical data under three
regimes and re-run the strategies:

* ``up``    - positive drift (like history): a geometric random walk up.
* ``down``  - negative drift: a geometric random walk down (secular bear).
* ``range`` - no drift, mean-reverting (Ornstein-Uhlenbeck): oscillates in a band.

These are deliberately simple log-return models, clearly labelled as synthetic.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Monthly parameters (sigma ~ 0.043/month is ~15%/yr, near the real S&P).
SIGMA = 0.043
UP_DRIFT = 0.0055      # ~ +6.8%/yr
DOWN_DRIFT = -0.0045   # ~ -5.3%/yr
REVERT_KAPPA = 0.04    # mean-reversion speed for the range regime
BASE = 100.0


def generate_market(dates: pd.Series, regime: str, rng: np.random.Generator) -> pd.DataFrame:
    """Generate one synthetic real-total-return path over ``dates``.

    Returns a DataFrame with ``date`` and ``real_total_return_index`` columns,
    matching what the backtest/dip functions expect.
    """
    dates = pd.to_datetime(pd.Series(dates).reset_index(drop=True))
    n = len(dates)
    log_base = np.log(BASE)

    if regime in ("up", "down"):
        mu = UP_DRIFT if regime == "up" else DOWN_DRIFT
        shocks = rng.normal(mu, SIGMA, n)
        shocks[0] = 0.0
        log_price = log_base + np.cumsum(shocks)
    elif regime == "range":
        # OU on the log price: pulled back toward log_base each month.
        log_price = np.empty(n)
        log_price[0] = log_base
        eps = rng.normal(0.0, SIGMA, n)
        for t in range(1, n):
            log_price[t] = log_price[t - 1] + REVERT_KAPPA * (log_base - log_price[t - 1]) + eps[t]
    else:
        raise ValueError(f"unknown regime: {regime}")

    return pd.DataFrame({"date": dates, "real_total_return_index": np.exp(log_price)})
