"""Per-strategy metrics and the rolling 40-year test harness."""

from __future__ import annotations

import pandas as pd

from . import utils
from .data import slice_window
from .dips import find_dip_bottoms_between_ath
from .strategies import (
    backtest_dca,
    backtest_delayed_buy_the_dip,
    backtest_god_buy_the_dip,
)

log = utils.get_logger()


def strategy_metrics(equity_curve: pd.DataFrame, trade_log: pd.DataFrame) -> dict:
    """Summary statistics for one strategy run over one window."""
    last = equity_curve.iloc[-1]
    final_value = last["portfolio_value"]
    total_contrib = equity_curve["contribution"].sum()
    ending_cash = last["cash"]
    ending_invested = last["shares"] * last["price"]
    n_purchases = len(trade_log)
    # Dollar-weighted average purchase price = total $ invested / total units bought.
    total_units = trade_log["shares_bought"].sum() if n_purchases else 0.0
    total_spent = trade_log["amount"].sum() if n_purchases else 0.0
    avg_price = (total_spent / total_units) if total_units else float("nan")
    return {
        "final_value": final_value,
        "total_contributions": total_contrib,
        "total_return_on_contributions": final_value / total_contrib - 1.0,
        "ending_cash": ending_cash,
        "ending_invested_value": ending_invested,
        "num_purchases": n_purchases,
        "avg_purchase_price": avg_price,
    }


def run_rolling_40_year_tests(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Run every rolling window and compare Buy the Dip variants to DCA.

    For each start year with enough data, runs DCA, God Buy the Dip and the
    delayed Buy the Dip variants, recording final values and the Buy-the-Dip
    outperformance ``btd_final / dca_final - 1``.
    """
    data_end = df["date"].iloc[-1]
    # Global dip bottoms computed once on the full history; each window uses only
    # the bottoms that fall inside it (see strategies / slice_window docstrings).
    global_bottoms = find_dip_bottoms_between_ath(df["real_total_return_index"], df["date"])
    bottom_dates = global_bottoms["bottom_date"].to_numpy()

    rows = []
    for start_year in range(config["start_year_min"], config["start_year_max"] + 1):
        start, end = utils.window_bounds(start_year, config["window_years"])
        if end > data_end:
            continue  # not enough data for a full window
        win = slice_window(df, start, end)
        if len(win) < config["window_years"] * 12:
            continue

        dca_curve, _ = backtest_dca(win, config["monthly_contribution"])
        god_curve, _ = backtest_god_buy_the_dip(
            win, config["monthly_contribution"], config["cash_return"], bottom_dates
        )
        dca_final = dca_curve["portfolio_value"].iloc[-1]
        god_final = god_curve["portfolio_value"].iloc[-1]

        row = {
            "start_year": start_year,
            "end_year": start_year + config["window_years"] - 1,
            "dca_final": dca_final,
            "god_btd_final": god_final,
            "god_btd_outperformance": god_final / dca_final - 1.0,
            "god_btd_beats_dca": god_final > dca_final,
        }
        for delay in config["delayed_btd_months"]:
            d_curve, _ = backtest_delayed_buy_the_dip(
                win, config["monthly_contribution"], delay, config["cash_return"], bottom_dates
            )
            d_final = d_curve["portfolio_value"].iloc[-1]
            row[f"delayed{delay}_final"] = d_final
            row[f"delayed{delay}_outperformance"] = d_final / dca_final - 1.0
            row[f"delayed{delay}_beats_dca"] = d_final > dca_final
        rows.append(row)
    return pd.DataFrame(rows)
