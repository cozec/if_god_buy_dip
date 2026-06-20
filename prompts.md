Build a Python project to reproduce and extend the analysis from Nick Maggiulli’s Of Dollars And Data post:
“Even God Couldn’t Beat Dollar-Cost Averaging”
URL: https://ofdollarsanddata.com/even-god-couldnt-beat-dollar-cost-averaging/

Goal:
Download historical U.S. stock market data, implement the DCA and “God Buy the Dip” strategies from the post, backtest rolling 40-year windows, and reproduce the major plots from the article.

Important:
The original post states that related code may be available in Nick Maggiulli’s GitHub repo:
https://github.com/nmaggiulli/of-dollars-and-data
The repo structure uses blog post numbers across import/build/analysis folders. The post is number 110. First, try to inspect files related to post 110 in the repo. If usable code or data exists, use it as reference, but still produce a clean Python implementation.

Use Python, not R.

Core strategy definitions:

1. Dollar-cost averaging strategy, DCA:
- Invest $100 every month.
- Investment happens at month-end or first available trading day after month-end; make this configurable.
- Buy the U.S. stock market index.
- Once shares are purchased, hold them until the end of the 40-year window.
- No selling.
- Use real total-return data if available. Prefer S&P 500 total return adjusted for inflation.
- If real total-return data is not available directly, build an approximation and clearly document it.

2. God Buy the Dip strategy:
- Save $100 every month as cash.
- Invest accumulated cash only at the exact lowest market point between two all-time highs.
- A “dip” means the market is below its previous all-time high.
- For every drawdown cycle:
  - Start at an all-time high.
  - Market falls below the all-time high.
  - Identify the minimum price before the next all-time high.
  - Invest all accumulated cash at that minimum point.
  - After buying, hold those shares until the end of the 40-year window.
- This strategy has perfect foresight, because it knows the exact bottom between two all-time highs.
- No selling after purchase.
- Cash earns 0% by default.
- Make optional cash interest configurable, default 0%.

3. Delayed Buy the Dip strategy:
- Same as God Buy the Dip, but instead of buying exactly at the bottom, buy 2 months after the bottom.
- If the buy date is not a trading day, use the next available trading day.
- This reproduces the article’s “miss the bottom by 2 months” test.
- Also make delay configurable: 1 month, 2 months, 3 months, 6 months.

Data requirements:
- Preferred historical range: 1920 through latest available.
- The article tests rolling 40-year periods starting from 1920 through 1979.
- Need monthly data.
- Need U.S. stock market total return, preferably S&P 500 total return including dividends and adjusted for inflation.
- Try these data sources in order:
  1. Robert Shiller data, if available, using S&P composite price, dividends, and CPI.
  2. FRED data if it provides usable S&P/CPI series.
  3. yfinance fallback using ^GSPC or SPY for modern periods only.
- Build a clean data loader that can support:
  - Shiller real total return series from 1920 onward.
  - yfinance adjusted close fallback for modern replication.
- Save raw and processed data to:
  data/raw/
  data/processed/

Data construction:
- If using Shiller data:
  - Download monthly S&P price, dividends, and CPI.
  - Construct nominal total-return index by reinvesting dividends.
  - Deflate by CPI to create real total-return index.
  - Normalize the real total-return index to 100 at the first date.
- Include comments explaining the total-return construction.
- Validate that monthly dates, prices, dividends, and CPI are aligned.
- Avoid lookahead bias except where explicitly required by “God Buy the Dip,” which intentionally uses future information.

Backtest windows:
- Rolling 40-year periods.
- Start years: 1920 through 1979, if data supports it.
- For each start year:
  - Start date: January of that year.
  - End date: December 40 years later, inclusive.
  - Example: 1920-1959, 1921-1960, etc., depending on exact month handling.
- Also include article-specific example windows:
  - 1995-2018, if modern data supports it.
  - 1928-1957.
  - 1975-2014.

Implementation details:
Create functions:

1. load_market_data()
- Downloads or loads market data.
- Returns monthly DataFrame with columns:
  - date
  - nominal_price
  - dividend
  - cpi
  - nominal_total_return_index
  - real_total_return_index
  - is_all_time_high

2. compute_all_time_highs(series)
- Returns rolling all-time high and boolean all-time-high markers.

3. find_dip_bottoms_between_ath(series)
- Identifies bottoms between all-time highs.
- For each interval between all-time highs:
  - Find minimum index value between ATH dates.
  - Mark that date as a God Buy the Dip purchase date.
- Important:
  - If market is at all-time high every month, there may be no dip.
  - Nested minor dips between frequent new highs should be captured.
  - For long bear markets, the major bottom should be captured before the next ATH.
- Return DataFrame with:
  - dip_start_ath_date
  - bottom_date
  - bottom_price
  - next_ath_date
  - drawdown_at_bottom

4. backtest_dca(window_data, monthly_contribution=100)
- Every month, invest $100.
- Track:
  - cash
  - shares
  - invested_amount
  - portfolio_value
  - contribution
  - shares_bought
- Return monthly equity curve and trade log.

5. backtest_god_buy_the_dip(window_data, monthly_contribution=100)
- Every month, add $100 to cash.
- If current month is a precomputed dip bottom date, invest all cash.
- Track:
  - cash
  - shares
  - invested_amount
  - portfolio_value
  - contribution
  - shares_bought
  - buy_marker
- Return monthly equity curve and trade log.

6. backtest_delayed_buy_the_dip(window_data, monthly_contribution=100, delay_months=2)
- Use bottom dates, but buy delay_months after the bottom.
- If delayed buy date is outside the 40-year window, do not buy.
- Return monthly equity curve and trade log.

7. run_rolling_40_year_tests()
- For every rolling 40-year start date:
  - Run DCA.
  - Run God Buy the Dip.
  - Run delayed Buy the Dip.
  - Record final values.
  - Record outperformance:
    buy_the_dip_final / dca_final - 1
  - Record whether Buy the Dip beat DCA.
- Return summary DataFrame.

8. calculate_purchase_growth()
- For each $100 monthly contribution, calculate what it grows to by the end of the window.
- For DCA, every month has one $100 purchase.
- For Buy the Dip, many monthly $100 contributions accumulate into cash and are invested together at dip bottoms.
- Return data needed for purchase growth bar charts.

Metrics:
For each strategy and each rolling window, calculate:
- Final portfolio value
- Total contributions
- Total return on contributions
- Ending cash
- Ending invested value
- Number of purchases
- Average purchase price
- Best and worst rolling window
- Buy the Dip outperformance vs DCA
- Percent of rolling windows where Buy the Dip beats DCA
- Percent of rolling windows where Buy the Dip underperforms DCA
- Same metrics for delayed Buy the Dip

Expected article-style findings to verify:
- God Buy the Dip should underperform DCA in more than 70% of 40-year windows.
- Delayed Buy the Dip with 2-month delay should underperform DCA in about 97% of windows.
- 1928-1957 should be favorable for Buy the Dip because it buys near the June 1932 bottom early.
- 1975-2014 should be bad for Buy the Dip because the next all-time high after the 1974 bear market does not arrive until much later.
- 1995-2018 should show a large Buy the Dip purchase around March 2009.

Plots to reproduce:

1. Market index with all-time highs
- Example period: 1995-2018.
- Plot real total-return index.
- Highlight all-time-high months in green.
- Save as:
  results/charts/01_market_with_all_time_highs_1995_2018.png

2. Market index with all-time highs and dip bottoms
- Same as plot 1.
- Add red dots for God Buy the Dip purchase dates.
- Save as:
  results/charts/02_market_with_dip_bottoms_1995_2018.png

3. Buy the Dip invested amount and cash balance
- Example period: 1995-2018.
- Plot cumulative amount invested and cash balance.
- Mark buy dates with red dots.
- Save as:
  results/charts/03_btd_invested_amount_and_cash_1995_2018.png

4. Portfolio value comparison
- Compare DCA vs God Buy the Dip.
- Example period: 1995-2018.
- Save as:
  results/charts/04_portfolio_value_dca_vs_btd_1995_2018.png

5. Purchase growth chart
- For each DCA monthly $100 purchase, show how much that purchase grows to by the end of the window.
- Overlay red dots for Buy the Dip purchase dates.
- Example period: 1995-2018.
- Save as:
  results/charts/05_purchase_growth_1995_2018.png

6. Purchase growth chart for 1928-1957
- Show why Buy the Dip works well when a major crash happens early.
- Save as:
  results/charts/06_purchase_growth_1928_1957.png

7. Rolling 40-year outperformance plot
- X-axis: start year.
- Y-axis: Buy the Dip final value / DCA final value - 1.
- Add horizontal line at 0%.
- Above 0 means Buy the Dip beat DCA.
- Below 0 means DCA beat Buy the Dip.
- Save as:
  results/charts/07_rolling_40yr_btd_outperformance.png

8. Portfolio value comparison for 1975-2014
- Compare DCA vs God Buy the Dip.
- Save as:
  results/charts/08_portfolio_value_dca_vs_btd_1975_2014.png

9. Purchase growth chart for 1975-2014
- Save as:
  results/charts/09_purchase_growth_1975_2014.png

10. Delayed Buy the Dip result
- Rolling 40-year outperformance of 2-month delayed Buy the Dip vs DCA.
- Save as:
  results/charts/10_rolling_40yr_delayed_btd_outperformance.png

Extra plots:
- Histogram of Buy the Dip outperformance across rolling windows.
- Bar chart of percent of windows where each strategy wins:
  - DCA
  - God Buy the Dip
  - Buy the Dip delayed by 1 month
  - Buy the Dip delayed by 2 months
  - Buy the Dip delayed by 3 months
  - Buy the Dip delayed by 6 months

Output files:
Save these CSVs:
- results/rolling_40yr_summary.csv
- results/example_1995_2018_equity_curves.csv
- results/example_1995_2018_trade_log_dca.csv
- results/example_1995_2018_trade_log_btd.csv
- results/dip_bottoms.csv
- results/purchase_growth_1995_2018.csv
- results/purchase_growth_1928_1957.csv
- results/purchase_growth_1975_2014.csv

Console output:
Print:
1. Data source used.
2. Date range available.
3. Number of rolling 40-year windows tested.
4. Percent of windows where God Buy the Dip beats DCA.
5. Percent of windows where God Buy the Dip underperforms DCA.
6. Percent of windows where 2-month delayed Buy the Dip underperforms DCA.
7. Best window for Buy the Dip vs DCA.
8. Worst window for Buy the Dip vs DCA.
9. Final values for the example windows:
   - 1995-2018
   - 1928-1957
   - 1975-2014

Project structure:
even_god_dca_backtest/
  README.md
  requirements.txt
  main.py
  src/
    data.py
    strategies.py
    dips.py
    metrics.py
    plots.py
    utils.py
  data/
    raw/
    processed/
  results/
    charts/

requirements.txt:
- pandas
- numpy
- matplotlib
- yfinance
- requests
- pandas_datareader, optional
- openpyxl, optional

Code quality requirements:
- Clean, modular code.
- No obscure packages.
- Use monthly data.
- Use adjusted / real total-return data where possible.
- Clearly separate data loading, backtesting, metrics, and plotting.
- Make assumptions explicit in comments and README.
- Add docstrings to all major functions.
- Include a top-level CONFIG section in main.py:
  - monthly_contribution = 100
  - start_year_min = 1920
  - start_year_max = 1979
  - window_years = 40
  - cash_return = 0.0
  - use_real_returns = True
  - execution_timing = "month_end"
  - delayed_btd_months = [1, 2, 3, 6]

Critical correctness notes:
- DCA invests immediately each month.
- Buy the Dip accumulates cash until a perfect hindsight bottom.
- The perfect bottom is the lowest point between two all-time highs.
- After any purchase, shares are held forever until the end of the window.
- Do not sell.
- Do not move in and out of stocks.
- The only deliberate lookahead is the God Buy the Dip strategy identifying future bottoms.
- For all performance comparisons, use the same contribution schedule and same market index.
- Avoid comparing price-only data to total-return data unless clearly labeled.

Deliverable:
Produce a complete runnable Python project. After running:

python main.py

it should:
1. Download/load data.
2. Build the real total-return market index.
3. Run all backtests.
4. Print summary statistics.
5. Save all CSVs.
6. Save all charts.
7. Confirm whether the reproduced results approximately match the article’s claims.