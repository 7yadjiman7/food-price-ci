"""Reusable analysis functions (used by the notebooks, the charts and the dashboard).

All functions take the clean DataFrame returned by `src.cleaning.clean`
and work on `price_xof_per_kg`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.config import STAPLES


def monthly_series(group: pd.DataFrame) -> pd.Series:
    """Price series of one commodity x market on a complete monthly calendar.
    Missing months become NaN instead of being silently skipped."""
    s = group.set_index("date")["price_xof_per_kg"].sort_index()
    s.index = s.index.to_period("M")
    return s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="M"))


# --- Q1. Price growth ------------------------------------------------------------

def price_growth(df: pd.DataFrame, commodities: list[str] = STAPLES,
                 min_years: float = 5) -> pd.DataFrame:
    """Annual growth rate (CAGR) of each commodity.

    For each commodity x market series covering at least `min_years`, compare the
    median price of its first 12 months with that of its last 12 months, then take
    the median across markets. Comparing within a market avoids confusing price
    changes with markets entering or leaving the dataset.
    """
    rows = []
    for (commodity, market), g in df[df["commodity"].isin(commodities)].groupby(["commodity", "market"]):
        start, end = g["date"].min(), g["date"].max()
        years = (end - start).days / 365.25
        if years < min_years:
            continue
        p_start = g.loc[g["date"] < start + pd.DateOffset(months=12), "price_xof_per_kg"].median()
        p_end = g.loc[g["date"] > end - pd.DateOffset(months=12), "price_xof_per_kg"].median()
        span = years - 1  # distance between the centres of the two 12-month windows
        rows.append({
            "commodity": commodity, "market": market,
            "start": start.year, "end": end.year,
            "total_change_pct": (p_end / p_start - 1) * 100,
            "cagr_pct": ((p_end / p_start) ** (1 / span) - 1) * 100,
        })
    per_series = pd.DataFrame(rows)
    return (
        per_series.groupby("commodity")
        .agg(n_markets=("market", "size"), first_year=("start", "min"), last_year=("end", "max"),
             median_cagr_pct=("cagr_pct", "median"),
             median_total_change_pct=("total_change_pct", "median"))
        .sort_values("median_cagr_pct", ascending=False)
    )


# --- Q2. Abidjan vs. other regions ---------------------------------------------------

def abidjan_gap(df: pd.DataFrame, min_months: int = 12, alpha: float = 0.05) -> pd.DataFrame:
    """Price gap between Abidjan and the median of the other markets, same product
    and same month. Wilcoxon signed-rank test with a Bonferroni correction."""
    abidjan = (df[df["admin1"] == "Abidjan"]
               .groupby(["commodity", "date"])["price_xof_per_kg"].median().rename("abidjan"))
    others = (df[df["admin1"] != "Abidjan"]
              .groupby(["commodity", "date"])["price_xof_per_kg"].median().rename("others"))
    paired = pd.concat([abidjan, others], axis=1, join="inner").reset_index()
    paired["log_gap"] = np.log(paired["abidjan"] / paired["others"])

    rows = []
    for commodity, g in paired.groupby("commodity"):
        if len(g) < min_months:
            continue
        rows.append({
            "commodity": commodity,
            "n_months": len(g),
            "median_gap_pct": (np.exp(g["log_gap"].median()) - 1) * 100,
            "p_value": stats.wilcoxon(g["log_gap"]).pvalue,
        })
    result = pd.DataFrame(rows).sort_values("median_gap_pct", ascending=False).reset_index(drop=True)
    result["significant"] = result["p_value"] < alpha / len(result)
    return result


# --- Q3. Seasonality ---------------------------------------------------------------

def seasonal_ratios(df: pd.DataFrame, commodities: list[str] = STAPLES,
                    min_months: int = 36) -> pd.DataFrame:
    """Price divided by its centred 12-month moving average (trend removed),
    for every commodity x market series with at least `min_months` of data."""
    parts = []
    for (commodity, market), g in df[df["commodity"].isin(commodities)].groupby(["commodity", "market"]):
        s = monthly_series(g)
        if s.notna().sum() < min_months:
            continue
        trend = s.interpolate(limit=2).rolling(12, center=True, min_periods=12).mean()
        ratio = (s / trend).dropna()
        parts.append(pd.DataFrame({"commodity": commodity, "market": market,
                                   "month": ratio.index.month, "ratio": ratio.values}))
    return pd.concat(parts, ignore_index=True)


def seasonal_profile(ratios: pd.DataFrame) -> pd.DataFrame:
    """Average % above/below trend for each commodity (rows) and calendar month (columns)."""
    return (ratios.groupby(["commodity", "month"])["ratio"].mean().unstack() - 1) * 100


def seasonality_tests(ratios: pd.DataFrame) -> pd.DataFrame:
    """Amplitude, peak/low month and Kruskal-Wallis p-value for each commodity."""
    profile = seasonal_profile(ratios)
    rows = []
    for commodity, g in ratios.groupby("commodity"):
        rows.append({
            "commodity": commodity,
            "n_markets": g["market"].nunique(),
            "amplitude_pct": profile.loc[commodity].max() - profile.loc[commodity].min(),
            "peak_month": profile.loc[commodity].idxmax(),
            "low_month": profile.loc[commodity].idxmin(),
            "kruskal_p": stats.kruskal(*[x["ratio"] for _, x in g.groupby("month")]).pvalue,
        })
    out = pd.DataFrame(rows).set_index("commodity").sort_values("amplitude_pct", ascending=False)
    out["significant"] = out["kruskal_p"] < 0.05
    return out


# --- Q4. Price shocks --------------------------------------------------------------

def rolling_z(s: pd.Series, window: int = 12, min_periods: int = 6) -> pd.DataFrame:
    """Rolling z-score of monthly log price changes.
    `.shift(1)`: each month is compared only with the months before it."""
    change = np.log(s).diff()
    past = change.shift(1).rolling(window, min_periods=min_periods)
    z = (change - past.mean()) / past.std()
    return pd.DataFrame({"price": s, "change": change, "z": z})


def detect_shocks(df: pd.DataFrame, z_threshold: float = 3.0,
                  min_change: float = 0.10) -> pd.DataFrame:
    """Rolling z-score for every commodity x market. A month is a shock when
    |z| > z_threshold AND the price moved by at least `min_change` (10%).
    The second condition avoids false alarms on prices that stay flat for months
    (rolling std close to 0)."""
    parts = []
    for (commodity, market), g in df.groupby(["commodity", "market"]):
        r = rolling_z(monthly_series(g))
        r["commodity"], r["market"] = commodity, market
        parts.append(r)
    z = pd.concat(parts).rename_axis("month").reset_index()
    z = z[np.isfinite(z["z"])].copy()
    z["shock"] = (z["z"].abs() > z_threshold) & (z["change"].abs() >= min_change)
    return z
