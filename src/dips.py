"""All-time-high detection and 'God Buy the Dip' bottom identification."""

from __future__ import annotations

import pandas as pd

# Relative tolerance for floating-point equality when flagging new highs.
_ATH_TOL = 1e-9


def compute_all_time_highs(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Return (running_max, is_all_time_high) for a price/level series.

    A month is an all-time high when its level is greater than or equal to every
    prior level (the running maximum). The first month is always an ATH.
    """
    running_max = series.cummax()
    is_ath = series >= running_max * (1 - _ATH_TOL)
    return running_max, is_ath


def find_dip_bottoms_between_ath(series: pd.Series, dates: pd.Series) -> pd.DataFrame:
    """Identify the lowest point in every drawdown between two all-time highs.

    For each pair of consecutive all-time-high months with sub-ATH months in
    between, the minimum level over that interval is the 'God Buy the Dip'
    purchase point - the strategy's deliberate, perfect-foresight lookahead.

    Notes
    -----
    * Adjacent ATH months (the market keeps making new highs) contain no dip.
    * Nested minor dips between frequent new highs are each captured.
    * A long bear market produces one bottom (its minimum) before the next ATH.
    * A trailing drawdown that never recovers to a new high *within the series*
      is intentionally **not** a buy point: the article only deploys cash at a
      confirmed bottom between two highs, so leftover cash stays uninvested.

    Returns a DataFrame with columns: dip_start_ath_date, bottom_date,
    bottom_price, next_ath_date, drawdown_at_bottom.
    """
    series = series.reset_index(drop=True)
    dates = dates.reset_index(drop=True)
    _, is_ath = compute_all_time_highs(series)
    ath_positions = [i for i, flag in enumerate(is_ath) if flag]

    rows = []
    for a, b in zip(ath_positions[:-1], ath_positions[1:]):
        if b == a + 1:
            continue  # consecutive highs -> no drawdown between them
        interval = series.iloc[a + 1 : b]          # strictly between the highs
        bottom_pos = interval.idxmin()
        ath_price = series.iloc[a]
        bottom_price = series.iloc[bottom_pos]
        rows.append(
            {
                "dip_start_ath_date": dates.iloc[a],
                "bottom_date": dates.iloc[bottom_pos],
                "bottom_price": bottom_price,
                "next_ath_date": dates.iloc[b],
                "drawdown_at_bottom": bottom_price / ath_price - 1.0,
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "dip_start_ath_date", "bottom_date", "bottom_price",
            "next_ath_date", "drawdown_at_bottom",
        ],
    )
