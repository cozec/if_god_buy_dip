"""Market-data loading and construction of a real total-return index.

Primary source: Robert Shiller's long-run monthly dataset (``ie_data.xls``),
which provides the S&P Composite price (``P``), the annualised dividend (``D``)
and the CPI back to 1871. From these we build a *nominal total-return* index by
reinvesting dividends, then deflate by CPI to get a *real total-return* index.

A yfinance fallback (``^GSPC``) is provided for modern-only replication when the
Shiller download is unavailable, but it is price-return / nominal and therefore
only a rough approximation - it is clearly labelled as such.
"""

from __future__ import annotations

import pandas as pd

from . import utils

SHILLER_URL = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"
SHILLER_RAW = utils.DATA_RAW / "shiller_ie_data.xls"
PROCESSED_CSV = utils.DATA_PROCESSED / "market_monthly.csv"

log = utils.get_logger()


# --------------------------------------------------------------------------- #
# Shiller download + parse
# --------------------------------------------------------------------------- #
def _download_shiller(force: bool = False) -> bool:
    """Download ``ie_data.xls`` into data/raw. Returns True on success."""
    if SHILLER_RAW.exists() and not force:
        return True
    try:
        import requests

        log.info("Downloading Shiller data from %s", SHILLER_URL)
        resp = requests.get(SHILLER_URL, timeout=60)
        resp.raise_for_status()
        SHILLER_RAW.write_bytes(resp.content)
        return True
    except Exception as exc:  # noqa: BLE001 - any failure -> fall back
        log.warning("Shiller download failed: %s", exc)
        return SHILLER_RAW.exists()


def _parse_shiller() -> pd.DataFrame:
    """Parse the Shiller 'Data' sheet into Date/P/D/CPI monthly columns.

    The header sits on row index 7 of the sheet; data starts on row 8. Trailing
    rows where the dividend is not yet published are dropped so the total-return
    construction is well defined for every row we keep.
    """
    df = pd.read_excel(SHILLER_RAW, sheet_name="Data", header=7)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[["Date", "P", "D", "CPI"]].copy()

    # Keep only genuine monthly rows (Date is numeric like 1871.01).
    df["Date"] = pd.to_numeric(df["Date"], errors="coerce")
    df = df[df["Date"].notna()]

    # Dividend / price / CPI must all be present to build the TR index.
    for col in ("P", "D", "CPI"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["P", "D", "CPI"]).reset_index(drop=True)

    df["date"] = df["Date"].map(utils.shiller_date_to_timestamp)
    return df.rename(columns={"P": "nominal_price", "D": "dividend", "CPI": "cpi"})[
        ["date", "nominal_price", "dividend", "cpi"]
    ]


def _build_total_return(df: pd.DataFrame) -> pd.DataFrame:
    """Construct nominal and real total-return indices from price/div/CPI.

    Total-return construction
    -------------------------
    Shiller's ``D`` is the *annualised* dividend per index unit, so the dividend
    actually received in a single month is ``D / 12``. Reinvesting it, the
    one-month gross total return is::

        r_t = (P_t + D_t / 12) / P_{t-1}

    The nominal total-return index is the cumulative product of ``r_t`` (seeded
    at 100 on the first month). Deflating by CPI converts nominal -> real::

        real_index_t = nominal_index_t * (CPI_0 / CPI_t)

    Finally the real index is renormalised to 100 on the first month so windows
    are easy to read. Buying/holding shares of this index is equivalent to
    reinvesting dividends in real terms, which is exactly what the article uses.
    """
    df = df.sort_values("date").reset_index(drop=True)

    # One-month gross total return with dividends reinvested (D is annualised).
    prev_price = df["nominal_price"].shift(1)
    monthly_div = df["dividend"] / 12.0
    gross = (df["nominal_price"] + monthly_div) / prev_price
    gross.iloc[0] = 1.0  # no return on the seed month

    nominal_tr = 100.0 * gross.cumprod()

    # Deflate to real terms using the first month's CPI as the base.
    cpi0 = df["cpi"].iloc[0]
    real_tr = nominal_tr * (cpi0 / df["cpi"])
    real_tr = real_tr / real_tr.iloc[0] * 100.0  # renormalise to 100

    df["nominal_total_return_index"] = nominal_tr
    df["real_total_return_index"] = real_tr
    return df


# --------------------------------------------------------------------------- #
# yfinance fallback (modern, price-return only)
# --------------------------------------------------------------------------- #
def _load_yfinance() -> pd.DataFrame:
    """Fallback: month-end ^GSPC adjusted close as a nominal index.

    This is a coarse approximation only: it is price-return (no separate
    dividend reinvestment beyond what 'Adj Close' captures) and is *not*
    inflation adjusted. Used solely so the pipeline still runs offline-of-Shiller.
    """
    import yfinance as yf

    log.warning("Falling back to yfinance ^GSPC (nominal, modern only).")
    raw = yf.download("^GSPC", start="1927-01-01", interval="1mo", auto_adjust=True, progress=False)
    close = raw["Close"].dropna()
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    df = pd.DataFrame({"date": close.index.to_period("M").to_timestamp(), "nominal_price": close.values})
    df["dividend"] = 0.0
    df["cpi"] = 1.0
    df["nominal_total_return_index"] = df["nominal_price"] / df["nominal_price"].iloc[0] * 100.0
    df["real_total_return_index"] = df["nominal_total_return_index"]
    return df


# --------------------------------------------------------------------------- #
# Modern extension: a consistent real-TR proxy past the end of Shiller's data
# --------------------------------------------------------------------------- #
FRED_CPI_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCNS"


def _load_modern_extension(shiller_df: pd.DataFrame) -> pd.DataFrame | None:
    """Chain-link a modern real total-return proxy onto the Shiller index.

    Shiller's file currently stops around mid-2023. To carry the *same* real
    total-return index forward we use a consistent proxy built from:

    * **S&P 500 Total Return index** (``^SP500TR``, yfinance) for the monthly
      *nominal* total return (dividends already reinvested), and
    * **CPI-U, not seasonally adjusted** (``CPIAUCNS``, FRED) for deflation -
      the same CPI family Shiller uses.

    The extension is *anchored* at Shiller's last value and grown by the proxy's
    monthly **real** return ``(TR_t/TR_{t-1}) * (CPI_{t-1}/CPI_t)``, so units and
    base (100 = 1871-01, real) stay identical. Rows are flagged
    ``is_modern_extension=True``.

    Caveat (documented, intentional): Shiller's price is a monthly *average*
    while ``^SP500TR`` is month-*end*, so the single splice month mixes
    conventions slightly. Returns ``None`` if either source is unavailable.
    """
    base_date = shiller_df["date"].iloc[-1]
    r0 = shiller_df["real_total_return_index"].iloc[-1]
    n0 = shiller_df["nominal_total_return_index"].iloc[-1]
    try:
        import io
        import urllib.request

        import yfinance as yf

        # Nominal total-return level (dividends reinvested), month-start index.
        raw = yf.download("^SP500TR", start="2023-01-01", interval="1mo",
                          auto_adjust=False, progress=False)
        tr = raw["Close"]
        if isinstance(tr, pd.DataFrame):
            tr = tr.iloc[:, 0]
        tr = pd.DataFrame({"date": tr.index.to_period("M").to_timestamp(), "tr": tr.values}).dropna()

        # CPI-U NSA from FRED (no API key needed).
        text = urllib.request.urlopen(FRED_CPI_URL, timeout=30).read().decode()
        cpi = pd.read_csv(io.StringIO(text))
        cpi.columns = ["date", "cpi"]
        cpi["date"] = pd.to_datetime(cpi["date"]).dt.to_period("M").dt.to_timestamp()
        cpi["cpi"] = pd.to_numeric(cpi["cpi"], errors="coerce")
    except Exception as exc:  # noqa: BLE001 - any failure -> skip extension
        log.warning("Modern extension unavailable (%s); using Shiller only.", exc)
        return None

    # Align on month, keep the anchor month plus everything after it.
    m = tr.merge(cpi, on="date", how="inner").sort_values("date").reset_index(drop=True)
    m = m[m["date"] >= base_date].reset_index(drop=True)
    # CPI can have an isolated interior gap (e.g. a delayed monthly release such
    # as Oct-2025); linearly interpolate those, then drop any trailing NaNs.
    m["cpi"] = m["cpi"].interpolate(method="linear", limit_area="inside")
    m = m.dropna(subset=["tr", "cpi"]).reset_index(drop=True)
    if m.empty or m["date"].iloc[0] != base_date:
        log.warning("Modern extension: anchor month %s missing; using Shiller only.", base_date.date())
        return None

    # Monthly real gross return relative to the previous month, then compound.
    real_gross = (m["tr"] / m["tr"].shift(1)) * (m["cpi"].shift(1) / m["cpi"])
    nom_gross = m["tr"] / m["tr"].shift(1)
    ext = m.iloc[1:].copy()  # drop the anchor row itself (it is Shiller's last)
    ext["real_total_return_index"] = r0 * real_gross.iloc[1:].cumprod().values
    ext["nominal_total_return_index"] = n0 * nom_gross.iloc[1:].cumprod().values
    ext["nominal_price"] = float("nan")  # proxy is a TR level, not a price
    ext["dividend"] = float("nan")        # dividends are embedded in ^SP500TR
    ext["is_modern_extension"] = True
    out = ext[["date", "nominal_price", "dividend", "cpi",
               "nominal_total_return_index", "real_total_return_index", "is_modern_extension"]]
    log.info("Modern extension: %d months %s to %s (^SP500TR x FRED CPIAUCNS).",
             len(out), out["date"].iloc[0].date(), out["date"].iloc[-1].date())
    return out


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def load_market_data(force_download: bool = False, modern_extension: bool = False) -> tuple[pd.DataFrame, str]:
    """Load monthly market data and build the real total-return index.

    Parameters
    ----------
    modern_extension : bool
        If True, append a clearly-labelled modern proxy (``^SP500TR`` deflated by
        FRED CPI) past the end of Shiller's data so windows reach the present.

    Returns
    -------
    (df, source) where ``df`` has columns::

        date, nominal_price, dividend, cpi,
        nominal_total_return_index, real_total_return_index,
        is_modern_extension, is_all_time_high

    and ``source`` is a human-readable description of the data origin.
    """
    from .dips import compute_all_time_highs  # local import avoids cycle

    if _download_shiller(force=force_download):
        df = _build_total_return(_parse_shiller())
        source = "Shiller ie_data.xls (real S&P total return, dividends reinvested, CPI-deflated)"
    else:
        df = _load_yfinance()
        source = "yfinance ^GSPC (NOMINAL price return, modern only - approximation)"

    df["is_modern_extension"] = False
    if modern_extension:
        ext = _load_modern_extension(df)
        if ext is not None and not ext.empty:
            df = pd.concat([df, ext], ignore_index=True)
            source += (f" + modern real-TR extension (^SP500TR x FRED CPIAUCNS) "
                       f"through {df['date'].iloc[-1].date()}")

    # All-time highs are computed on the FULL (possibly extended) real series.
    df["is_all_time_high"] = compute_all_time_highs(df["real_total_return_index"])[1].values

    cols = [
        "date", "nominal_price", "dividend", "cpi",
        "nominal_total_return_index", "real_total_return_index",
        "is_modern_extension", "is_all_time_high",
    ]
    df = df[cols]
    df.to_csv(PROCESSED_CSV, index=False)
    log.info("Loaded %d monthly rows: %s to %s", len(df),
             df["date"].iloc[0].date(), df["date"].iloc[-1].date())
    return df, source


def slice_window(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Return the window subset, preserving the *global* all-time-high flags.

    All-time highs are an objective market fact, not relative to when an
    investor started: "the dip" means below the market's previous all-time high.
    An investor starting in 1975 is still below the 1973 peak, so the market is
    in a drawdown that produces no *new* highs (and therefore no dip-buys) for
    years - which is exactly why God Buy the Dip's cash sits idle in that window.
    Keeping the global flags here is what reproduces the article's behaviour.
    """
    return df[(df["date"] >= start) & (df["date"] <= end)].copy().reset_index(drop=True)
