# Summary — Even God Couldn't Beat Dollar-Cost Averaging

Reproduction of Maggiulli's result using **Shiller real S&P total return**
(dividends reinvested, CPI-deflated), monthly, $100/month contributions.

- **Data source:** Shiller `ie_data.xls`, real total-return index, 1871-01 → 2023-06,
  **extended to 2026-05** by a consistent modern proxy (`^SP500TR` × FRED `CPIAUCNS`,
  chain-linked; rows flagged `is_modern_extension`).
- **Rolling windows:** 67 windows, start years 1920–1986 (auto-extended to the
  latest the data supports; last window 1986–2025), each 40 years (480 months).
  The 3 newest windows (1984–1986 starts) use the modern extension.
- **All-time highs / dip bottoms:** computed globally on full history (see README).

## Headline result — rolling 40-year windows

| Strategy | % of windows that beat DCA | % that underperform DCA |
|---|---:|---:|
| **DCA** | — (benchmark) | — |
| God Buy the Dip (perfect bottom) | **31.3%** | **68.7%** |
| Delayed Buy the Dip — 1 month | 25.4% | 74.6% |
| Delayed Buy the Dip — 2 months | **3.0%** | **97.0%** |
| Delayed Buy the Dip — 3 months | 0.0% | 100.0% |
| Delayed Buy the Dip — 6 months | 1.5% | 98.5% |

Full 67-window set (1920–1986, incl. modern extension). On the article-comparable
pre-extension subset (64 windows, 1920–1983): God BTD underperforms **71.9%**,
2-month delay **96.9%** — the newest windows catch the 2009/2020 bottoms, nudging
God's full-set underperformance down to 68.7%.

- Best window for God BTD: **1928–1967**, +21.6% vs DCA (buys the June 1932 bottom).
- Worst window for God BTD: **1975–2014**, −17.3% vs DCA (misses the 1974 bottom).

### Article-claim checks (all PASS)

| Claim (article) | Reproduced | Status |
|---|---|---|
| God BTD underperforms DCA in >70% of windows (comparable subset) | 71.9% | ✅ |
| 2-month delay underperforms DCA ~97% (comparable subset) | 96.9% | ✅ |
| 1928–1957 favourable for BTD | BTD +22.6% | ✅ |
| 1975–2014 unfavourable for BTD | BTD −17.3% | ✅ |
| 1995–2018 shows a large BTD buy at March 2009 | $10,600 lump, = 52% of final value | ✅ |

## Example windows — strategy comparison (ordered by final equity)

Real dollars; $100/month; "Return on contributions" = final / total contributed − 1.

**1995–2018** (288 months, $28,800 contributed):

| Strategy | Final equity | Return on contrib. | End cash | # purchases | Avg purchase price |
|---|---:|---:|---:|---:|---:|
| God Buy the Dip | $71,454 | +148.1% | $0 | 26 | 597,213 |
| DCA | $61,760 | +114.4% | $0 | 288 | 920,602 |

**1928–1957** (360 months, $36,000 contributed):

| Strategy | Final equity | Return on contrib. | End cash | # purchases | Avg purchase price |
|---|---:|---:|---:|---:|---:|
| God Buy the Dip | $187,465 | +420.7% | $100 | many small + 1932 bottom | low |
| DCA | $152,866 | +324.6% | $0 | 360 | higher |

**1975–2014** (480 months, $48,000 contributed):

| Strategy | Final equity | Return on contrib. | End cash | Notes |
|---|---:|---:|---:|---|
| DCA | $296,451 | +517.6% | $0 | invests every month immediately |
| God Buy the Dip | $245,145 | +410.7% | $200 | cash idle for years; misses 1974 bottom |

> Note the direction flips by window: BTD wins when a deep crash occurs *early*
> (1928, 1995-2018 via 2009) and loses when the window opens mid-recovery with
> no new highs for years (1975).

## God BTD trade log — 1995–2018 (26 trades, logged per house rules)

The single March-2009 lump ($10,600) grows to $37,091 — **51.9%** of the final
$71,454 portfolio, reproducing the article's "~52% of final value" point.

| # | Date | Index level | Amount invested | Grows to (real $) |
|---|------|------------:|----------------:|------------------:|
| 1 | 1996-01 | 445,088 | $1,300 | $5,094 |
| 2 | 1996-04 | 465,635 | $300 | $1,124 |
| 3 | 1996-07 | 463,849 | $300 | $1,128 |
| 4 | 1997-04 | 547,411 | $900 | $2,868 |
| 5 | 1997-11 | 673,943 | $700 | $1,812 |
| 6 | 1998-06 | 795,178 | $700 | $1,535 |
| 7 | 1998-09 | 732,256 | $300 | $715 |
| 8 | 1999-02 | 894,633 | $500 | $975 |
| 9 | 1999-06 | 943,362 | $400 | $740 |
| 10 | 1999-10 | 920,073 | $400 | $758 |
| 11 | 2000-02 | 977,556 | $400 | $714 |
| 12 | 2000-05 | 991,375 | $300 | $528 |
| 13 | **2009-03** | **498,468** | **$10,600** | **$37,091** |
| 14 | 2013-06 | 1,060,992 | $5,100 | $8,384 |
| 15 | 2014-02 | 1,200,256 | $800 | $1,163 |
| 16 | 2014-04 | 1,223,522 | $200 | $285 |
| 17 | 2014-08 | 1,291,429 | $400 | $540 |
| 18 | 2014-10 | 1,281,900 | $200 | $272 |
| 19 | 2015-01 | 1,370,053 | $300 | $382 |
| 20 | 2015-03 | 1,395,222 | $200 | $250 |
| 21 | 2016-02 | 1,296,746 | $1,100 | $1,480 |
| 22 | 2016-10 | 1,451,633 | $800 | $961 |
| 23 | 2017-04 | 1,595,835 | $600 | $656 |
| 24 | 2017-08 | 1,665,412 | $400 | $419 |
| 25 | 2018-04 | 1,785,157 | $800 | $782 |
| 26 | 2018-12 | 1,744,206 | $800 | $800 |

(The two largest buys, 2009-03 and 2013-06, follow the 2007-09 crash; earlier
small buys are minor pullbacks during the late-1990s bull run.)

## Major real dip bottoms found (full history)

| Bottom date | Real drawdown |
|---|---:|
| 1920-12 | −47% |
| 1932-06 | −77% (Great Depression) |
| 1942-04 | −48% |
| 1974-12 | −50% |
| 2009-03 | −52% |

## Reproducibility

`python main.py` regenerates every CSV in `results/`, all charts in
`results/charts/`, and `logs/run.log`. Conclusion: **reproduced — even with
perfect foresight, Buy the Dip loses to DCA in ~70% of windows** (71.9% on the
article-comparable subset; 68.7% over the full set extended to 2025), and missing
the bottom by just two months pushes that to ~97%.
