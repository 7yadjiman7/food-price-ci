"""The three communication charts. Each chart title IS its one-sentence takeaway.

    python -m src.charts   # writes reports/figures/*.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no window needed: figures are written to files
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.analysis import abidjan_gap, price_growth, seasonal_profile, seasonal_ratios  # noqa: E402
from src.cleaning import clean, load_raw  # noqa: E402
from src.config import FIGURES_DIR  # noqa: E402

HIGHLIGHT = "#C0392B"
MUTED = "#B8BEC6"
GREY = "#7F8C8D"
TEXT = "#2C3E50"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
SOURCE = "Source: WFP food prices for Côte d'Ivoire, via HDX (licence CC BY-IGO)."

plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#888888", "text.color": TEXT, "axes.labelcolor": TEXT,
})


def _finish(fig: plt.Figure, title: str, note: str, path: Path) -> Path:
    """Takeaway as a left-aligned title over the whole figure, method + source note at the bottom."""
    fig.suptitle(title, x=0.01, ha="left", fontsize=13.5, fontweight="bold", color=TEXT)
    fig.text(0.01, 0.012, f"{note}\n{SOURCE}", fontsize=8.5, color="#777777")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor="white")
    plt.close(fig)
    return path


def chart_price_growth(df: pd.DataFrame, path: Path) -> Path:
    growth = price_growth(df)
    growth = growth[growth["n_markets"] >= 3].sort_values("median_cagr_pct")

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [HIGHLIGHT if v > 3 else MUTED for v in growth["median_cagr_pct"]]
    ax.barh(growth.index, growth["median_cagr_pct"], color=colors)
    ax.axvline(3, color="#555555", ls="--", lw=1)
    ax.text(3.08, -0.85, "3%/year: WAEMU inflation ceiling", fontsize=9, va="bottom")
    for y, (v, total) in enumerate(zip(growth["median_cagr_pct"], growth["median_total_change_pct"])):
        ax.text(v + 0.12, y, f"{v:.1f}%/yr  (+{total:.0f}% in total)", va="center", fontsize=9.5)
    ax.set_xlim(0, growth["median_cagr_pct"].max() + 3.5)
    ax.set_ylim(-0.9, len(growth) - 0.5)
    ax.set_xlabel("Median annual price increase (% per year)")
    ax.grid(axis="x", alpha=0.3)
    title = ("Most staples rose faster than the 3% inflation ceiling:\n"
             "yam +9% a year, maize +5%, cassava and rice about +4%")
    note = ("Same-market comparison of the first and last 12 months of each series (at least 5 years), "
            "products seen in 3+ markets.")
    return _finish(fig, title, note, path)


def chart_abidjan_premium(df: pd.DataFrame, path: Path) -> Path:
    gap = abidjan_gap(df).sort_values("median_gap_pct")
    colors = [HIGHLIGHT if s else MUTED for s in gap["significant"]]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(gap["commodity"], gap["median_gap_pct"], color=colors)
    ax.axvline(0, color="#555555", lw=0.8)
    for y, v in enumerate(gap["median_gap_pct"]):
        ax.text(v + (1.5 if v >= 0 else -1.5), y, f"{v:+.0f}%", va="center",
                ha="left" if v >= 0 else "right", fontsize=9.5)
    ax.set_xlim(gap["median_gap_pct"].min() - 12, gap["median_gap_pct"].max() + 12)
    ax.set_xlabel("Price in Abidjan compared with the rest of the country (same product, same month)")
    ax.grid(axis="x", alpha=0.3)
    title = ("Over 2011-2021, local staples cost up to 77% more in Abidjan,\n"
             "while imported rice costs about the same everywhere")
    note = ("Median monthly gap. Red = statistically significant (Wilcoxon test, Bonferroni-corrected). "
            "Abidjan = Adjamé market, 2011-2021.")
    return _finish(fig, title, note, path)


def chart_seasonality(df: pd.DataFrame, path: Path) -> Path:
    profile = seasonal_profile(seasonal_ratios(df))
    lines = {  # commodity: (label, colour, label nudge)
        "Maize": ("Maize", HIGHLIGHT, 0),
        "Cassava (fresh)": ("Cassava (fresh)", "#E67E22", 0.35),
        "Rice (local)": ("Rice (local)", "#2980B9", -0.35),
        "Rice (denikassia, imported)": ("Imported rice", GREY, 0),
    }

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axvspan(3.5, 7.5, color="#F5B7B1", alpha=0.25, lw=0)
    ax.text(5.5, 7.4, "lean season", ha="center", fontsize=9.5, color="#A93226")
    ax.axhline(0, color="#555555", lw=0.8)
    for commodity, (label, color, nudge) in lines.items():
        values = profile.loc[commodity]
        imported = color == GREY
        ax.plot(range(1, 13), values, marker="o", color=color,
                lw=1.8 if imported else 2.2, ls="--" if imported else "-")
        ax.text(12.25, values.iloc[-1] + nudge, label, va="center", fontsize=9.5, color=color)
    ax.set_xticks(range(1, 13), MONTHS)
    ax.set_xlim(0.7, 14.6)
    ax.set_ylabel("% above / below the long-term trend")
    ax.grid(axis="y", alpha=0.3)
    title = ("Local staples peak in the lean season and fall 6-7% below trend after the harvest,\n"
             "while imported rice prices do not follow the seasons")
    note = ("Average over all markets with at least 3 years of data; long-term trend removed with a "
            "12-month moving average.")
    return _finish(fig, title, note, path)


def make_all(df: pd.DataFrame | None = None, out_dir: Path = FIGURES_DIR) -> list[Path]:
    df = clean(load_raw()) if df is None else df
    return [
        chart_price_growth(df, out_dir / "1_price_growth.png"),
        chart_abidjan_premium(df, out_dir / "2_abidjan_premium.png"),
        chart_seasonality(df, out_dir / "3_seasonality.png"),
    ]


if __name__ == "__main__":
    for p in make_all():
        print(f"Saved {p}")
