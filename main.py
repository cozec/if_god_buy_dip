"""Reproduce "Even God Couldn't Beat Dollar-Cost Averaging" (Of Dollars And Data).

Run with::

    python main.py

It loads Shiller's monthly data, builds a real total-return index, runs DCA,
God Buy the Dip and Delayed Buy the Dip over rolling 40-year windows plus three
illustrative windows, then writes CSVs and charts and prints a summary that is
checked against the article's headline claims.
"""

from __future__ import annotations

import pandas as pd

from src import plots, utils
from src.data import load_market_data, slice_window
from src.dips import find_dip_bottoms_between_ath
from src.metrics import run_rolling_40_year_tests, strategy_metrics
from src.strategies import (
    backtest_dca,
    backtest_delayed_buy_the_dip,
    backtest_god_buy_the_dip,
    calculate_purchase_growth,
)

# --------------------------------------------------------------------------- #
# CONFIG
# --------------------------------------------------------------------------- #
CONFIG = {
    "monthly_contribution": 100.0,
    "start_year_min": 1920,
    "start_year_max": 1979,
    "window_years": 40,
    "cash_return": 0.0,           # annual interest earned on uninvested cash
    "use_real_returns": True,     # use CPI-deflated total-return index
    "execution_timing": "month_end",
    "delayed_btd_months": [1, 2, 3, 6],
}

# Illustrative (non-rolling) windows used for the article's example charts.
EXAMPLE_WINDOWS = {"1995_2018": (1995, 2018), "1928_1957": (1928, 1957), "1975_2014": (1975, 2014)}

log = utils.get_logger()


def _example_window(df: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    start = pd.Timestamp(start_year, 1, 1)
    end = pd.Timestamp(end_year, 12, 1)
    return slice_window(df, start, end)


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def main() -> None:
    utils.ensure_dirs()

    # 1. Load data + build real total-return index ------------------------- #
    df, source = load_market_data()
    win_count_data = df["date"].iloc[0], df["date"].iloc[-1]

    # 2. Rolling 40-year tests --------------------------------------------- #
    summary = run_rolling_40_year_tests(df, CONFIG)
    summary.to_csv(utils.RESULTS / "rolling_40yr_summary.csv", index=False)

    n_windows = len(summary)
    god_beats = summary["god_btd_beats_dca"].mean() * 100
    god_under = 100 - god_beats
    delayed2_under = (~summary["delayed2_beats_dca"]).mean() * 100
    best = summary.loc[summary["god_btd_outperformance"].idxmax()]
    worst = summary.loc[summary["god_btd_outperformance"].idxmin()]

    # Global dip bottoms (perfect-foresight buy points) computed once; each
    # window uses only the bottoms inside it.
    full_bottoms = find_dip_bottoms_between_ath(df["real_total_return_index"], df["date"])
    full_bottoms.to_csv(utils.RESULTS / "dip_bottoms.csv", index=False)
    global_bottom_dates = full_bottoms["bottom_date"].to_numpy()

    # 3. Example windows: backtests, CSVs, dip bottoms --------------------- #
    examples = {}
    for key, (sy, ey) in EXAMPLE_WINDOWS.items():
        win = _example_window(df, sy, ey)
        dca_curve, dca_trades = backtest_dca(win, CONFIG["monthly_contribution"])
        god_curve, god_trades = backtest_god_buy_the_dip(
            win, CONFIG["monthly_contribution"], CONFIG["cash_return"], global_bottom_dates)
        # Bottoms inside this window, for plotting.
        bottoms = full_bottoms[
            (full_bottoms["bottom_date"] >= win["date"].iloc[0])
            & (full_bottoms["bottom_date"] <= win["date"].iloc[-1])
        ].reset_index(drop=True)
        examples[key] = {
            "win": win, "dca_curve": dca_curve, "dca_trades": dca_trades,
            "god_curve": god_curve, "god_trades": god_trades, "bottoms": bottoms,
            "dca_metrics": strategy_metrics(dca_curve, dca_trades),
            "god_metrics": strategy_metrics(god_curve, god_trades),
        }

    # CSVs for the 1995-2018 example.
    ex = examples["1995_2018"]
    pd.DataFrame({
        "date": ex["dca_curve"]["date"],
        "dca_portfolio_value": ex["dca_curve"]["portfolio_value"],
        "god_btd_portfolio_value": ex["god_curve"]["portfolio_value"],
        "god_btd_cash": ex["god_curve"]["cash"],
        "god_btd_invested": ex["god_curve"]["invested_amount"],
    }).to_csv(utils.RESULTS / "example_1995_2018_equity_curves.csv", index=False)
    ex["dca_trades"].to_csv(utils.RESULTS / "example_1995_2018_trade_log_dca.csv", index=False)
    ex["god_trades"].to_csv(utils.RESULTS / "example_1995_2018_trade_log_btd.csv", index=False)

    # Purchase-growth CSVs for the three example windows.
    for key in EXAMPLE_WINDOWS:
        pg = calculate_purchase_growth(examples[key]["win"], examples[key]["dca_trades"])
        pg.to_csv(utils.RESULTS / f"purchase_growth_{key}.csv", index=False)

    # 4. Charts ------------------------------------------------------------ #
    e = examples["1995_2018"]
    plots.plot_market_with_ath(e["win"], "01_market_with_all_time_highs_1995_2018.png",
                               "实际总回报指数与历史新高（1995–2018）")
    plots.plot_market_with_dip_bottoms(e["win"], e["bottoms"], "02_market_with_dip_bottoms_1995_2018.png",
                                       "历史新高与上帝抄底的回调最低点（1995–2018）")
    # Zoomed view of chart 02 over a sub-range, to inspect the dip bottoms closely.
    zs, ze = pd.Timestamp(2016, 1, 1), pd.Timestamp(2018, 12, 1)
    z_win = e["win"][(e["win"]["date"] >= zs) & (e["win"]["date"] <= ze)].reset_index(drop=True)
    z_bottoms = e["bottoms"][(e["bottoms"]["bottom_date"] >= zs) & (e["bottoms"]["bottom_date"] <= ze)]
    plots.plot_market_with_dip_bottoms(z_win, z_bottoms, "02b_market_with_dip_bottoms_2016_2018.png",
                                       "历史新高与抄底最低点（放大：2016–2018）")
    plots.plot_btd_invested_and_cash(e["god_curve"], "03_btd_invested_amount_and_cash_1995_2018.png",
                                     "上帝抄底：已投入金额与现金余额（1995–2018）")
    plots.plot_portfolio_comparison(e["dca_curve"], e["god_curve"], "04_portfolio_value_dca_vs_btd_1995_2018.png",
                                    "组合价值：定投 vs 上帝抄底（1995–2018）")
    plots.plot_purchase_growth(calculate_purchase_growth(e["win"], e["dca_trades"]),
                               calculate_purchase_growth(e["win"], e["god_trades"]),
                               "05_purchase_growth_1995_2018.png", "每笔投入的增长（1995–2018）")

    e28 = examples["1928_1957"]
    plots.plot_purchase_growth(calculate_purchase_growth(e28["win"], e28["dca_trades"]),
                               calculate_purchase_growth(e28["win"], e28["god_trades"]),
                               "06_purchase_growth_1928_1957.png",
                               "每笔投入的增长（1928–1957）：早期崩盘有利抄底")

    plots.plot_rolling_outperformance(summary, "god_btd_outperformance",
                                      "07_rolling_40yr_btd_outperformance.png",
                                      "上帝抄底 vs 定投，滚动40年窗口")

    e75 = examples["1975_2014"]
    plots.plot_portfolio_comparison(e75["dca_curve"], e75["god_curve"],
                                    "08_portfolio_value_dca_vs_btd_1975_2014.png",
                                    "组合价值：定投 vs 上帝抄底（1975–2014）")
    plots.plot_purchase_growth(calculate_purchase_growth(e75["win"], e75["dca_trades"]),
                               calculate_purchase_growth(e75["win"], e75["god_trades"]),
                               "09_purchase_growth_1975_2014.png", "每笔投入的增长（1975–2014）")

    plots.plot_rolling_outperformance(summary, "delayed2_outperformance",
                                      "10_rolling_40yr_delayed_btd_outperformance.png",
                                      "延迟2个月抄底 vs 定投，滚动40年窗口")

    # Extra charts.
    plots.plot_outperformance_histogram(summary, "11_btd_outperformance_histogram.png",
                                        "上帝抄底相对定投的超额收益分布")
    win_rates = {"上帝抄底": god_beats}
    for d in CONFIG["delayed_btd_months"]:
        win_rates[f"延迟{d}月"] = summary[f"delayed{d}_beats_dca"].mean() * 100
    plots.plot_win_rate_bars(win_rates, "12_win_rate_by_strategy.png",
                             "各策略跑赢定投的窗口比例")

    # 5. Console summary --------------------------------------------------- #
    print("\n" + "=" * 70)
    print("EVEN GOD COULDN'T BEAT DCA - reproduction summary")
    print("=" * 70)
    print(f"1. Data source            : {source}")
    print(f"2. Date range available   : {win_count_data[0].date()} to {win_count_data[1].date()}")
    print(f"3. Rolling 40yr windows   : {n_windows} "
          f"({summary['start_year'].min()}-{summary['start_year'].max()} starts)")
    print(f"4. God BTD beats DCA      : {_pct(god_beats/100)} of windows")
    print(f"5. God BTD underperforms  : {_pct(god_under/100)} of windows")
    print(f"6. 2m Delayed underperf.  : {_pct(delayed2_under/100)} of windows")
    print(f"7. Best window for BTD    : {int(best['start_year'])}-{int(best['end_year'])}  "
          f"({_pct(best['god_btd_outperformance'])} vs DCA)")
    print(f"8. Worst window for BTD   : {int(worst['start_year'])}-{int(worst['end_year'])}  "
          f"({_pct(worst['god_btd_outperformance'])} vs DCA)")
    print("9. Example window final values (real $):")
    for key, (sy, ey) in EXAMPLE_WINDOWS.items():
        dm = examples[key]["dca_metrics"]
        gm = examples[key]["god_metrics"]
        print(f"   {sy}-{ey}: DCA=${dm['final_value']:,.0f}  "
              f"God BTD=${gm['final_value']:,.0f}  "
              f"(BTD/DCA-1 = {_pct(gm['final_value']/dm['final_value']-1)}, "
              f"end cash=${gm['ending_cash']:,.0f})")

    # 6. Verify against article claims ------------------------------------- #
    print("\n" + "-" * 70)
    print("ARTICLE CLAIM CHECKS")
    print("-" * 70)
    checks = [
        ("God BTD underperforms DCA in >70% of windows", god_under > 70),
        ("2-month delay underperforms DCA in ~97% of windows", delayed2_under >= 90),
        ("1928-1957 favourable for BTD (BTD beats DCA)",
         examples["1928_1957"]["god_metrics"]["final_value"]
         > examples["1928_1957"]["dca_metrics"]["final_value"]),
        ("1975-2014 unfavourable for BTD (DCA beats BTD)",
         examples["1975_2014"]["god_metrics"]["final_value"]
         < examples["1975_2014"]["dca_metrics"]["final_value"]),
        ("1995-2018 has a big BTD buy around 2009",
         any((pd.to_datetime(examples["1995_2018"]["god_trades"]["date"]).dt.year.between(2008, 2009))
             & (examples["1995_2018"]["god_trades"]["amount"]
                == examples["1995_2018"]["god_trades"]["amount"].max()))),
    ]
    for desc, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {desc}")

    print("\nDone. CSVs in results/, charts in results/charts/, log in logs/run.log")


if __name__ == "__main__":
    main()
