"""Shared helpers: paths, logging, and small date utilities.

This module centralises filesystem layout so every other module agrees on
where raw data, processed data, results, charts and logs live.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------- #
# Project layout (hybrid: root-level project, results/charts for plots).
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
RESULTS = ROOT / "results"
CHARTS = RESULTS / "charts"
LOGS = ROOT / "logs"


def ensure_dirs() -> None:
    """Create all output directories if they do not already exist."""
    for d in (DATA_RAW, DATA_PROCESSED, RESULTS, CHARTS, LOGS):
        d.mkdir(parents=True, exist_ok=True)


def get_logger(name: str = "god_buy_dip") -> logging.Logger:
    """Return a logger that writes both to stdout and logs/run.log."""
    ensure_dirs()
    logger = logging.getLogger(name)
    if logger.handlers:  # already configured
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")

    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    fileh = logging.FileHandler(LOGS / "run.log", mode="w")
    fileh.setFormatter(fmt)
    logger.addHandler(fileh)
    return logger


def shiller_date_to_timestamp(value: float) -> pd.Timestamp:
    """Convert a Shiller ``YYYY.MM`` float (e.g. ``1871.10``) to a month-start
    ``Timestamp``.

    Shiller encodes the month in the first two decimals, so October 1871 is
    ``1871.10`` and January 1871 is ``1871.01``. Floating point noise is
    removed with ``round``.
    """
    year = int(value)
    month = int(round((value - year) * 100))
    return pd.Timestamp(year=year, month=month, day=1)


def window_bounds(start_year: int, window_years: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return (start, end) month-start timestamps for a calendar window.

    Following the article's examples (``1920-1959`` is one window), a
    ``window_years``-long window starting in ``start_year`` runs from January of
    ``start_year`` to December of ``start_year + window_years - 1`` inclusive.
    """
    start = pd.Timestamp(year=start_year, month=1, day=1)
    end = pd.Timestamp(year=start_year + window_years - 1, month=12, day=1)
    return start, end
