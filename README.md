# Even God Couldn't Beat Dollar-Cost Averaging

A clean Python reproduction (and extension) of Nick Maggiulli's *Of Dollars And
Data* post **["Even God Couldn't Beat Dollar-Cost Averaging"](https://ofdollarsanddata.com/even-god-couldnt-beat-dollar-cost-averaging/)**.

It builds a real (inflation-adjusted) total-return index for the U.S. stock
market from Robert Shiller's monthly dataset, then backtests three strategies
over rolling 40-year windows:

| Strategy | Rule |
|---|---|
| **DCA** | Invest $100 every month, immediately, and hold forever. |
| **God Buy the Dip** | Save $100/month as cash; invest *all* cash at the exact lowest point between two all-time highs (perfect foresight). |
| **Delayed Buy the Dip** | Same, but buy `N` months *after* each bottom (N = 1, 2, 3, 6). |

The headline finding: even with a perfect crystal ball for market bottoms, God
Buy the Dip **underperforms DCA in ~72% of 40-year windows**, because cash sits
idle (earning nothing) while it waits for dips that may be years away.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

`main.py` downloads the data (cached after first run), builds the index, runs
all backtests, prints a summary, and writes every CSV and chart.

## Data & the real total-return index

Primary source: **Shiller `ie_data.xls`** (S&P Composite price `P`, annualised
dividend `D`, CPI), monthly back to 1871.

The real total-return index is built so that buying and holding it is equivalent
to a dividend-reinvested, inflation-adjusted buy-and-hold position:

1. Monthly dividend received = `D / 12` (Shiller's `D` is annualised).
2. One-month gross total return `r_t = (P_t + D_t/12) / P_{t-1}`.
3. Nominal total-return index = cumulative product of `r_t`, seeded at 100.
4. Deflate by CPI (`× CPI_0 / CPI_t`) and renormalise to 100 → **real** index.

A **yfinance `^GSPC`** fallback exists for offline/modern-only runs, but it is
nominal price-return only and clearly labelled as an approximation.

## Key modelling decision: all-time highs are *global*

"The dip" means below the market's *previous all-time high* — an objective
market fact, not relative to when an investor started. So all-time highs and dip
bottoms are computed once on the full history, and each window invests only at
the bottoms that fall inside it. This is what reproduces the article's behaviour:
an investor starting in **1975** is still below the 1973 peak, so the market
makes no new highs (and offers no dip to buy) for ~a decade — God's cash sits
idle and DCA wins handily. Resetting highs per-window instead would invent fake
early dips and wrongly flip that result.

The only deliberate lookahead is God's knowledge of future bottoms. Nothing is
ever sold; every purchase is held to the end of the window.

## Project layout

```
god_buy_dip/
  main.py              # CONFIG + full pipeline
  src/
    data.py            # load_market_data, slice_window, real TR construction
    dips.py            # compute_all_time_highs, find_dip_bottoms_between_ath
    strategies.py      # backtest_dca / god / delayed, calculate_purchase_growth
    metrics.py         # strategy_metrics, run_rolling_40_year_tests
    plots.py           # all charts
    utils.py           # paths, logging, date helpers
  data/raw/            # downloaded Shiller xls
  data/processed/      # market_monthly.csv
  results/             # summary CSVs
  results/charts/      # 12 PNG charts
  logs/                # run.log
```

## Configuration (`CONFIG` in `main.py`)

```python
monthly_contribution = 100
start_year_min       = 1920
start_year_max       = 1979       # floor; auto-extended at runtime to the latest
                                  # year the data supports (currently 1983 -> 1983-2022)
window_years         = 40        # a window is Jan(start)..Dec(start+39), e.g. 1920-1959
cash_return          = 0.0       # annual interest on uninvested cash
use_real_returns     = True
execution_timing     = "month_end"
delayed_btd_months   = [1, 2, 3, 6]
```

## Outputs

- `results/rolling_40yr_summary.csv` — per-window finals & outperformance.
- `results/dip_bottoms.csv` — every global dip bottom (date, price, drawdown).
- `results/example_1995_2018_*` — equity curves and DCA/BTD trade logs.
- `results/purchase_growth_{1995_2018,1928_1957,1975_2014}.csv`.
- `results/charts/01..12_*.png` — the 10 article charts plus a distribution
  histogram and a per-strategy win-rate bar chart.

See `summary.md` for the reproduced numbers and how they line up with the
article's claims.

## Assumptions & caveats

- Shiller `D` is treated as the annualised dividend; monthly cash flow = `D/12`.
- A window of `window_years` runs Jan(start) → Dec(start+years-1) inclusive,
  matching the article's `1920-1959` example (480 months).
- Trailing cash: if a window ends mid-drawdown with no confirmed next high, God's
  remaining cash stays uninvested (a real, intended drag).
- Cash earns `cash_return` (default 0%); configurable.
- Results use the Shiller file's range (currently through mid-2023). The rolling
  test auto-extends `start_year_max` to the latest year with a complete 40-year
  window — currently **1983 starts → 1983-2022**, 64 windows in total. It will
  reach further automatically whenever Shiller publishes newer months.
