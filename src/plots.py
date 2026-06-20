"""All chart generation. Uses a non-interactive backend so it runs headless."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import utils

# Use a CJK-capable font so all in-chart text renders in Chinese.
plt.rcParams["font.family"] = "Arial Unicode MS"
plt.rcParams["axes.unicode_minus"] = False  # avoid tofu for the minus sign

GREEN, RED, BLUE, ORANGE = "#2ca02c", "#d62728", "#1f77b4", "#ff7f0e"


def _save(fig, name: str) -> None:
    path = utils.CHARTS / name
    fig.tight_layout()
    fig.savefig(path, dpi=200)  # high-res so the web page stays sharp when zoomed
    plt.close(fig)


def plot_market_with_ath(win: pd.DataFrame, name: str, title: str) -> None:
    """Real total-return index with all-time-high months highlighted green."""
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(win["date"], win["real_total_return_index"], color=BLUE, lw=1.3, label="实际总回报指数")
    ath = win[win["is_all_time_high"]]
    ax.scatter(ath["date"], ath["real_total_return_index"], color=GREEN, s=12, label="历史新高", zorder=3)
    ax.set_title(title)
    ax.set_ylabel("指数（实际，起点=100）")
    ax.legend()
    _save(fig, name)


def plot_market_with_dip_bottoms(win: pd.DataFrame, bottoms: pd.DataFrame, name: str, title: str) -> None:
    """As above, plus red dots at God Buy the Dip purchase (bottom) dates."""
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(win["date"], win["real_total_return_index"], color=BLUE, lw=1.3, label="实际总回报指数")
    ath = win[win["is_all_time_high"]]
    ax.scatter(ath["date"], ath["real_total_return_index"], color=GREEN, s=12, label="历史新高", zorder=3)
    if not bottoms.empty:
        ax.scatter(bottoms["bottom_date"], bottoms["bottom_price"], color=RED, s=45,
                   marker="o", label="回调最低点（上帝买入）", zorder=4)
    ax.set_title(title)
    ax.set_ylabel("指数（实际，起点=100）")
    ax.legend()
    _save(fig, name)


def plot_btd_invested_and_cash(god_curve: pd.DataFrame, name: str, title: str) -> None:
    """Buy the Dip cash allocation as stacked areas (invested + cash), with buys.

    Invested + cash always sums to total contributions to date, so the two bands
    stack to a staircase; cash builds up then collapses into 'invested' at each
    perfect-bottom purchase (red dots).
    """
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.stackplot(
        god_curve["date"],
        god_curve["invested_amount"],
        god_curve["cash"],
        labels=["已投入市场", "等待中的现金"],
        colors=[BLUE, ORANGE],
        alpha=0.85,
    )
    buys = god_curve[god_curve["buy_marker"]]
    ax.scatter(buys["date"], buys["invested_amount"], color=RED, s=45, zorder=5, label="抄底买入")
    ax.set_title(title)
    ax.set_ylabel("累计投入（美元）")
    ax.legend(loc="upper left")
    _save(fig, name)


def plot_portfolio_comparison(dca_curve: pd.DataFrame, god_curve: pd.DataFrame, name: str, title: str) -> None:
    """DCA vs God Buy the Dip portfolio value over time."""
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(dca_curve["date"], dca_curve["portfolio_value"], color=BLUE, lw=1.6, label="定投 DCA")
    ax.plot(god_curve["date"], god_curve["portfolio_value"], color=RED, lw=1.6, label="上帝抄底")
    ax.set_title(title)
    ax.set_ylabel("组合价值（实际美元）")
    ax.legend()
    _save(fig, name)


def plot_purchase_growth(dca_growth: pd.DataFrame, btd_growth: pd.DataFrame, name: str, title: str) -> None:
    """Final value of each $100 DCA purchase (black bars), with red dots marking
    the months Buy the Dip purchased - placed at that month's bar height, as in
    the article. The tallest bar (the best month to have invested) is annotated.
    """
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(dca_growth["date"], dca_growth["final_value"], width=20, color="black",
           label="每 $100 定投 → 最终价值")

    # Red dots at the bar height for the months Buy the Dip actually bought.
    if not btd_growth.empty:
        heights = dca_growth.set_index("date")["final_value"]
        marks = btd_growth.assign(h=btd_growth["date"].map(heights)).dropna(subset=["h"])
        ax.scatter(marks["date"], marks["h"], color=RED, s=40, zorder=4, label="抄底买入月份")

    # Annotate the single best purchase month (the article's highlight).
    top = dca_growth.loc[dca_growth["final_value"].idxmax()]
    ax.annotate(f"{pd.Timestamp(top['date']):%Y年%m月}：$100 → ${top['final_value']:,.0f}",
                xy=(top["date"], top["final_value"]),
                xytext=(0.30, 0.92), textcoords="axes fraction",
                arrowprops=dict(arrowstyle="->", color="gray"), fontsize=9)
    ax.set_title(title)
    ax.set_ylabel("每笔投入的最终价值（实际美元）")
    ax.legend()
    _save(fig, name)


def plot_rolling_outperformance(summary: pd.DataFrame, col: str, name: str, title: str,
                                mark_year: int | None = None, mark_label: str | None = None) -> None:
    """Line of Buy-the-Dip outperformance vs DCA by window start year (as in the
    article): above the zero line = Buy the Dip wins, below = DCA wins.

    If ``mark_year`` is given, shade window start years >= that year and draw a
    dashed line to flag windows whose data includes the modern extension.
    """
    fig, ax = plt.subplots(figsize=(11, 5))
    pct = summary[col] * 100
    ax.plot(summary["start_year"], pct, color=BLUE, lw=1.6)
    ax.fill_between(summary["start_year"], pct, 0, where=pct >= 0, color=GREEN, alpha=0.30)
    ax.fill_between(summary["start_year"], pct, 0, where=pct < 0, color=RED, alpha=0.30)
    ax.axhline(0, color="black", lw=0.9)
    if mark_year is not None:
        ax.axvspan(mark_year - 0.5, summary["start_year"].max() + 0.5, color="#9467bd", alpha=0.12)
        ax.axvline(mark_year - 0.5, color="#9467bd", lw=1.2, ls="--")
        ax.text(mark_year - 0.5, ax.get_ylim()[1] * 0.92, "  " + (mark_label or "含现代延伸数据"),
                color="#5b2d8e", fontsize=9, va="top")
    below = (pct < 0).mean() * 100
    ax.set_title(f"{title}（定投在 {below:.0f}% 的窗口胜出）")
    ax.set_xlabel("窗口起始年")
    ax.set_ylabel("抄底 ÷ 定投 − 1（%）")
    _save(fig, name)


def plot_outperformance_histogram(summary: pd.DataFrame, name: str, title: str) -> None:
    """Histogram of God Buy the Dip outperformance across all windows."""
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(summary["god_btd_outperformance"] * 100, bins=20, color=BLUE, alpha=0.8)
    ax.axvline(0, color=RED, lw=1.2, label="定投持平线")
    ax.set_title(title)
    ax.set_xlabel("抄底相对定投的超额收益（%）")
    ax.set_ylabel("窗口数量")
    ax.legend()
    _save(fig, name)


def plot_win_rate_bars(win_rates: dict, name: str, title: str) -> None:
    """Bar chart: % of windows each strategy beats/ties DCA."""
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = list(win_rates.keys())
    values = [win_rates[k] for k in labels]
    ax.bar(labels, values, color=BLUE)
    ax.set_title(title)
    ax.set_ylabel("跑赢定投的窗口比例（%）")
    ax.set_ylim(0, 100)
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    _save(fig, name)
