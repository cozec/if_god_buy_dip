"""Backtest engines for DCA, God Buy the Dip and Delayed Buy the Dip.

All strategies share the same contribution schedule ($100/month) and the same
real total-return index, so their final values are directly comparable. The
'price' a strategy trades at is the real total-return index level; buying one
unit and holding it is equivalent to a dividend-reinvested, inflation-adjusted
buy-and-hold position. Nothing is ever sold.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .dips import find_dip_bottoms_between_ath

PRICE_COL = "real_total_return_index"


def _monthly_cash_factor(cash_return: float) -> float:
    """Convert an annual cash interest rate to a monthly growth factor."""
    return (1.0 + cash_return) ** (1.0 / 12.0)


def backtest_dca(window_data: pd.DataFrame, monthly_contribution: float = 100.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Invest a fixed amount every month and hold forever.

    Returns (equity_curve, trade_log). DCA never holds cash: each month's
    contribution immediately buys ``contribution / price`` units.
    """
    prices = window_data[PRICE_COL].to_numpy()
    dates = window_data["date"].to_numpy()

    shares = 0.0
    invested = 0.0
    curve, trades = [], []
    for i, price in enumerate(prices):
        bought = monthly_contribution / price
        shares += bought
        invested += monthly_contribution
        value = shares * price
        curve.append(
            {"date": dates[i], "price": price, "contribution": monthly_contribution,
             "shares_bought": bought, "cash": 0.0, "shares": shares,
             "invested_amount": invested, "portfolio_value": value}
        )
        trades.append({"date": dates[i], "price": price, "amount": monthly_contribution, "shares_bought": bought})
    return pd.DataFrame(curve), pd.DataFrame(trades)


def _resolve_bottom_dates(window_data: pd.DataFrame, bottom_dates) -> set:
    """Return the set of dip-bottom dates to use for a window.

    ``bottom_dates`` should be the *global* dip bottoms (computed once on the
    full history); only those falling inside the window matter. If omitted, they
    are computed from the window itself - convenient for standalone use but note
    that global bottoms are what reproduce the article (see ``slice_window``).
    """
    if bottom_dates is None:
        bottoms = find_dip_bottoms_between_ath(window_data[PRICE_COL], window_data["date"])
        return set(pd.to_datetime(bottoms["bottom_date"]).to_numpy())
    return set(pd.to_datetime(pd.Series(list(bottom_dates))).to_numpy())


def backtest_god_buy_the_dip(
    window_data: pd.DataFrame,
    monthly_contribution: float = 100.0,
    cash_return: float = 0.0,
    bottom_dates=None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Accumulate cash and deploy it all at each perfect-hindsight dip bottom.

    Bottoms are the minima between consecutive all-time highs (see
    :func:`find_dip_bottoms_between_ath`), passed in as global ``bottom_dates``.
    On a bottom month, the current month's contribution is added to cash first,
    then the entire cash balance is invested. Any cash still uninvested at window
    end is left as cash (drag) - including when the window starts mid-drawdown
    and the relevant bottom already passed before the investor began.
    """
    prices = window_data[PRICE_COL].to_numpy()
    dates = window_data["date"].to_numpy()

    buy_dates = _resolve_bottom_dates(window_data, bottom_dates)
    cash_factor = _monthly_cash_factor(cash_return)

    cash = 0.0
    shares = 0.0
    invested = 0.0
    curve, trades = [], []
    for i, price in enumerate(prices):
        cash = cash * cash_factor + monthly_contribution  # interest, then save
        is_buy = dates[i] in buy_dates
        bought = 0.0
        if is_buy and cash > 0:
            bought = cash / price
            shares += bought
            invested += cash
            cash = 0.0
            trades.append({"date": dates[i], "price": price, "amount": bought * price, "shares_bought": bought})
        curve.append(
            {"date": dates[i], "price": price, "contribution": monthly_contribution,
             "shares_bought": bought, "cash": cash, "shares": shares,
             "invested_amount": invested, "portfolio_value": shares * price + cash,
             "buy_marker": bool(is_buy and bought > 0)}
        )
    return pd.DataFrame(curve), pd.DataFrame(trades)


def backtest_delayed_buy_the_dip(
    window_data: pd.DataFrame,
    monthly_contribution: float = 100.0,
    delay_months: int = 2,
    cash_return: float = 0.0,
    bottom_dates=None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """God Buy the Dip but each purchase happens ``delay_months`` after the bottom.

    Buys whose delayed date falls outside the window are skipped (their cash
    keeps accumulating and rolls into the next executed buy).
    """
    prices = window_data[PRICE_COL].to_numpy()
    dates = window_data["date"].to_numpy()
    n = len(prices)

    buy_dates = _resolve_bottom_dates(window_data, bottom_dates)
    date_to_pos = {d: i for i, d in enumerate(dates)}
    buy_positions = set()
    for bd in buy_dates:
        if bd not in date_to_pos:
            continue  # bottom itself is outside this window
        pos = date_to_pos[bd] + delay_months
        if pos < n:  # delayed buy date still inside the window
            buy_positions.add(pos)

    cash_factor = _monthly_cash_factor(cash_return)
    cash = 0.0
    shares = 0.0
    invested = 0.0
    curve, trades = [], []
    for i, price in enumerate(prices):
        cash = cash * cash_factor + monthly_contribution
        is_buy = i in buy_positions
        bought = 0.0
        if is_buy and cash > 0:
            bought = cash / price
            shares += bought
            invested += cash
            cash = 0.0
            trades.append({"date": dates[i], "price": price, "amount": bought * price, "shares_bought": bought})
        curve.append(
            {"date": dates[i], "price": price, "contribution": monthly_contribution,
             "shares_bought": bought, "cash": cash, "shares": shares,
             "invested_amount": invested, "portfolio_value": shares * price + cash,
             "buy_marker": bool(is_buy and bought > 0)}
        )
    return pd.DataFrame(curve), pd.DataFrame(trades)


def calculate_purchase_growth(window_data: pd.DataFrame, trade_log: pd.DataFrame) -> pd.DataFrame:
    """How much each purchase grows to by the end of the window.

    A purchase of ``amount`` at ``price`` grows to ``amount * final_price/price``
    by the last month (no selling). For DCA there is one $100 purchase per month;
    for Buy the Dip there are a few large lump-sum purchases at the dip bottoms.

    Returns one row per trade: date, price, amount, growth_factor, final_value.
    """
    final_price = window_data[PRICE_COL].iloc[-1]
    out = trade_log.copy()
    if out.empty:
        return pd.DataFrame(columns=["date", "price", "amount", "growth_factor", "final_value"])
    out["growth_factor"] = final_price / out["price"]
    out["final_value"] = out["amount"] * out["growth_factor"]
    return out[["date", "price", "amount", "growth_factor", "final_value"]]
