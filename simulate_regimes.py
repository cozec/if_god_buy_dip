"""Run DCA vs God Buy the Dip across synthetic market regimes.

Usage::

    python simulate_regimes.py

Monte-Carlos synthetic 'down' (secular bear) and 'range' (mean-reverting) paths
over the *same* dates as the historical data, runs rolling 40-year DCA vs God Buy
the Dip on each, and reports how often God beats DCA. The real historical market
is the 'up' reference. The point: God's dip-buying only loses in an up-trending
market - DCA's edge is the upward drift, not the timing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src import plots, utils  # importing plots sets the CJK font for charts
from src.metrics import run_rolling_40_year_tests
from src.simulate import generate_market
from src.strategies import backtest_dca, backtest_god_buy_the_dip
from src.dips import find_dip_bottoms_between_ath

import matplotlib.pyplot as plt

N_PATHS = 80                       # Monte-Carlo paths per regime
# Monte-Carlo the two regimes the user asked about; the real historical market is
# used as the "up" reference (a genuine, persistently up-trending market).
REGIMES = ["down", "range"]
REP_REGIMES = ["up", "down", "range"]   # also generate an 'up' path for visuals
REGIME_ZH = {"up": "上涨市（合成·对照）", "down": "下跌市", "range": "区间震荡市"}
BLUE, RED, GREEN, PURPLE = "#1f77b4", "#d62728", "#2ca02c", "#9467bd"

# Same contribution / window rules as the main analysis; no delayed variants and
# a single 40-year length keep the Monte-Carlo fast.
SIM_CONFIG = {
    "monthly_contribution": 100.0,
    "start_year_min": 1920,
    "start_year_max": 1986,
    "window_years": 40,
    "cash_return": 0.0,
    "delayed_btd_months": [],
}


def _dates() -> pd.Series:
    """Reuse the historical monthly date index so the time range is identical."""
    df = pd.read_csv(utils.DATA_PROCESSED / "market_monthly.csv", usecols=["date"], parse_dates=["date"])
    return df["date"]


def main() -> None:
    utils.ensure_dirs()
    dates = _dates()
    print(f"Synthetic dates: {dates.iloc[0].date()} to {dates.iloc[-1].date()} "
          f"({len(dates)} months); {N_PATHS} paths/regime\n")

    # Representative path (seed 0) per regime, for the visual figures.
    rep_paths = {r: generate_market(dates, r, np.random.default_rng(0)) for r in REP_REGIMES}

    rows = []
    for regime in REGIMES:
        beats, outperf = [], []
        for seed in range(N_PATHS):
            rng = np.random.default_rng(seed)
            sim = generate_market(dates, regime, rng)
            summary = run_rolling_40_year_tests(sim, SIM_CONFIG)
            beats.append(summary["god_btd_beats_dca"].to_numpy())
            outperf.append(summary["god_btd_outperformance"].to_numpy())
        beats = np.concatenate(beats)
        outperf = np.concatenate(outperf)
        rows.append({
            "regime": regime,
            "god_beats_dca_pct": beats.mean() * 100,
            "median_outperformance_pct": np.median(outperf) * 100,
            "n_window_samples": len(beats),
        })
        print(f"{REGIME_ZH[regime]:<6} | God beats DCA in {beats.mean()*100:5.1f}% of windows "
              f"| median BTD/DCA-1 = {np.median(outperf)*100:+6.1f}%")

    res = pd.DataFrame(rows)
    res.to_csv(utils.RESULTS / "simulation_regimes.csv", index=False)

    # Historical reference (real up-trending market) from the main run, if present.
    hist_pct = None
    hist_csv = utils.RESULTS / "rolling_40yr_summary.csv"
    if hist_csv.exists():
        hist_pct = pd.read_csv(hist_csv)["god_btd_beats_dca"].mean() * 100
        print(f"\n参考·历史真实市场 | God beats DCA in {hist_pct:5.1f}% of windows")

    _plot_paths(rep_paths)
    _plot_winrates(res, hist_pct)
    _plot_example_portfolios(rep_paths)
    print("\nDone. Charts: results/charts/sim_*.png ; table: results/simulation_regimes.csv")


def _plot_paths(rep_paths: dict) -> None:
    """Representative synthetic price path for each regime (seed 0)."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for ax, regime in zip(axes, REP_REGIMES):
        s = rep_paths[regime]
        ax.plot(s["date"], s["real_total_return_index"], color=BLUE, lw=1.0)
        ax.set_title(REGIME_ZH[regime])
        ax.set_yscale("log")
        ax.set_ylabel("指数（对数，合成）")
    fig.suptitle("三种合成市场的代表性走势（相同时间区间）", fontsize=13)
    fig.tight_layout()
    fig.savefig(utils.CHARTS / "sim_01_representative_paths.png", dpi=200)
    plt.close(fig)


def _plot_winrates(res: pd.DataFrame, hist_pct: float | None) -> None:
    """Bar chart: % of windows God beats DCA, by regime (+ historical)."""
    labels = [REGIME_ZH[r] for r in res["regime"]]
    vals = list(res["god_beats_dca_pct"])
    colors = [GREEN if v >= 50 else RED for v in vals]
    if hist_pct is not None:
        labels.append("历史真实市场")
        vals.append(hist_pct)
        colors.append(RED if hist_pct < 50 else GREEN)

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, vals, color=colors)
    ax.axhline(50, color="black", lw=0.9, ls="--")
    ax.text(len(labels) - 0.5, 51, "50% 分水岭", ha="right", fontsize=9)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:.0f}%", ha="center", fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_ylabel("上帝抄底跑赢定投的窗口比例（%）")
    ax.set_title("不同市场环境下：上帝抄底能否战胜定投？")
    fig.tight_layout()
    fig.savefig(utils.CHARTS / "sim_02_winrate_by_regime.png", dpi=200)
    plt.close(fig)


def _plot_example_portfolios(rep_paths: dict) -> None:
    """One representative 40-year window per regime: DCA vs God portfolio value."""
    start = pd.Timestamp(SIM_CONFIG["start_year_min"], 1, 1)
    end = pd.Timestamp(SIM_CONFIG["start_year_min"] + SIM_CONFIG["window_years"] - 1, 12, 1)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    for ax, regime in zip(axes, REP_REGIMES):
        s = rep_paths[regime]
        win = s[(s["date"] >= start) & (s["date"] <= end)].reset_index(drop=True)
        bottoms = find_dip_bottoms_between_ath(win["real_total_return_index"], win["date"])
        dca, _ = backtest_dca(win, SIM_CONFIG["monthly_contribution"])
        god, _ = backtest_god_buy_the_dip(win, SIM_CONFIG["monthly_contribution"],
                                          SIM_CONFIG["cash_return"], bottoms["bottom_date"].to_numpy())
        ax.plot(dca["date"], dca["portfolio_value"], color=BLUE, lw=1.4, label="定投 DCA")
        ax.plot(god["date"], god["portfolio_value"], color=RED, lw=1.4, label="上帝抄底")
        winner = "上帝抄底胜" if god["portfolio_value"].iloc[-1] > dca["portfolio_value"].iloc[-1] else "定投胜"
        ax.set_title(f"{REGIME_ZH[regime]}（{start.year}-{end.year}）— {winner}")
        ax.set_ylabel("组合价值（合成）")
        ax.legend()
    fig.suptitle("代表性 40 年窗口：定投 vs 上帝抄底", fontsize=13)
    fig.tight_layout()
    fig.savefig(utils.CHARTS / "sim_03_example_portfolios.png", dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    main()
