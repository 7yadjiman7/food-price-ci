"""Reusable cleaning pipeline for the WFP food prices dataset (Côte d'Ivoire).

Usage from a notebook:
    from src.cleaning import load_raw, clean
    df = clean(load_raw())

Usage from a terminal (project root):
    python -m src.cleaning
"""

from __future__ import annotations

import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import PROCESSED_PATH, RAW_PATH

# --- Unit normalisation tables -------------------------------------------------

# Mass of one base unit, in kg.
MASS_UNITS_KG = {"KG": 1.0, "G": 0.001, "MT": 1000.0}

# Volume of one base unit, in litres (converted to kg with DENSITY_KG_PER_L).
VOLUME_UNITS_L = {"L": 1.0, "ML": 0.001}

# Approximate densities (kg per litre) for products sold by volume.
DENSITY_KG_PER_L = {
    "Oil (palm)": 0.91,
    "Oil (vegetable)": 0.92,
    "Fuel (petrol-gasoline)": 0.74,
}

# Product names that refer to the same item.
COMMODITY_ALIASES = {
    "Groundnuts": "Peanut",
}

CONSTANT_COLUMNS_OK_TO_DROP = ["pricetype", "currency"]


# --- Steps ---------------------------------------------------------------------

def load_raw(path: str | Path = RAW_PATH) -> pd.DataFrame:
    """Read the raw CSV (downloaded from HDX if missing).
    Skips the HXL tag row (#date, #adm1...) that HDX files often contain."""
    path = Path(path)
    if not path.exists():
        from src.download import download
        download(path)
    df = pd.read_csv(path, encoding="utf-8")
    if str(df.iloc[0, 0]).startswith("#"):
        df = df.iloc[1:].reset_index(drop=True)
    return df


def parse_types(df: pd.DataFrame) -> pd.DataFrame:
    """Give each column its proper dtype."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    for col in ["price", "usdprice", "latitude", "longitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["market_id", "commodity_id"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    for col in ["admin1", "admin2", "market", "category", "commodity",
                "unit", "priceflag", "pricetype", "currency"]:
        df[col] = df[col].astype("string").str.strip()
    return df


def drop_constant_columns(df: pd.DataFrame,
                          columns: list[str] = CONSTANT_COLUMNS_OK_TO_DROP) -> pd.DataFrame:
    """Drop columns that hold a single value (they carry no information)."""
    to_drop = [c for c in columns if c in df.columns and df[c].nunique(dropna=False) <= 1]
    return df.drop(columns=to_drop)


def harmonize_commodities(df: pd.DataFrame,
                          aliases: dict[str, str] = COMMODITY_ALIASES) -> pd.DataFrame:
    """Merge product names that designate the same item."""
    df = df.copy()
    df["commodity"] = df["commodity"].replace(aliases)
    return df


def unit_to_kg(unit: str, commodity: str | None = None) -> float:
    """Return how many kg one `unit` represents, e.g. 'KG' -> 1, '50 KG' -> 50,
    'L' for palm oil -> 0.91. Returns NaN if the unit cannot be converted."""
    match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)?\s*([A-Za-z]+)\s*", str(unit))
    if not match:
        return np.nan
    qty = float(match.group(1).replace(",", ".")) if match.group(1) else 1.0
    base = match.group(2).upper()

    if base in MASS_UNITS_KG:
        return qty * MASS_UNITS_KG[base]
    if base in VOLUME_UNITS_L:
        density = DENSITY_KG_PER_L.get(commodity)
        return qty * VOLUME_UNITS_L[base] * density if density else np.nan
    return np.nan


def normalize_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Add `kg_per_unit`, `price_xof_per_kg` and `price_usd_per_kg`.

    The original `price`, `usdprice` and `unit` columns are kept for traceability.
    """
    df = df.copy()
    pairs = df[["unit", "commodity"]].drop_duplicates()
    pairs["kg_per_unit"] = [unit_to_kg(u, c) for u, c in zip(pairs["unit"], pairs["commodity"])]
    df = df.merge(pairs, on=["unit", "commodity"], how="left")

    unknown = df.loc[df["kg_per_unit"].isna(), ["commodity", "unit"]].drop_duplicates()
    if not unknown.empty:
        warnings.warn(f"Units not convertible to kg (rows kept, price set to NaN):\n{unknown}")

    df["price_xof_per_kg"] = (df["price"] / df["kg_per_unit"]).round(2)
    df["price_usd_per_kg"] = (df["usdprice"] / df["kg_per_unit"]).round(4)
    return df


def remove_invalid_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop exact duplicates and rows with missing or non-positive prices."""
    df = df.drop_duplicates()
    return df[df["price"].notna() & (df["price"] > 0)].copy()


def flag_outliers(df: pd.DataFrame, k: float = 3.0) -> pd.DataFrame:
    """Flag (not remove) prices far from the usual level of each commodity x market.

    Uses a robust z-score: |x - median| / (1.4826 * MAD) > k, computed on log prices.
    """
    df = df.copy()
    log_p = np.log(df["price_xof_per_kg"])
    grp = log_p.groupby([df["commodity"], df["market"]])
    median = grp.transform("median")
    mad = (log_p - median).abs().groupby([df["commodity"], df["market"]]).transform("median")
    robust_z = (log_p - median) / (1.4826 * mad.replace(0, np.nan))
    df["is_outlier"] = robust_z.abs() > k
    return df


# --- Full pipeline -------------------------------------------------------------

def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Run every cleaning step in order and return the clean dataset."""
    return (
        df.pipe(parse_types)
          .pipe(remove_invalid_rows)
          .pipe(drop_constant_columns)
          .pipe(harmonize_commodities)
          .pipe(normalize_prices)
          .pipe(flag_outliers)
          .sort_values(["commodity", "market", "date"])
          .reset_index(drop=True)
    )


def save_processed(df: pd.DataFrame, path: str | Path = PROCESSED_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return path


if __name__ == "__main__":
    clean_df = clean(load_raw())
    out = save_processed(clean_df)
    print(f"{len(clean_df)} rows saved to {out}")
    print(f"Outliers flagged: {int(clean_df['is_outlier'].sum())}")
