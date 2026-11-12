"""Unit tests for the cleaning and analysis functions (no download needed).

    python -m pytest
"""

import math

import numpy as np
import pandas as pd
import pytest

from src.analysis import detect_shocks
from src.cleaning import clean, unit_to_kg


def make_raw(rows: list[dict]) -> pd.DataFrame:
    base = {
        "admin1": "Gbeke", "admin2": "Gbeke", "market": "Bouake", "market_id": 1,
        "latitude": 7.7, "longitude": -5.0, "category": "cereals and tubers",
        "commodity": "Maize", "commodity_id": 51, "unit": "KG", "priceflag": "actual",
        "pricetype": "Retail", "currency": "XOF", "usdprice": 0.5,
    }
    return pd.DataFrame([{**base, **r} for r in rows])


@pytest.mark.parametrize("unit, commodity, expected", [
    ("KG", None, 1.0),
    ("50 KG", None, 50.0),
    ("100 G", None, 0.1),
    ("L", "Oil (palm)", 0.91),
])
def test_unit_to_kg(unit, commodity, expected):
    assert unit_to_kg(unit, commodity) == pytest.approx(expected)


def test_unit_to_kg_unknown_unit_is_nan():
    assert math.isnan(unit_to_kg("Bunch"))
    assert math.isnan(unit_to_kg("L", "Unknown liquid"))


def test_clean_normalises_to_xof_per_kg_and_drops_bad_rows():
    raw = make_raw([
        {"date": "2020-01-15", "price": 500, "unit": "50 KG"},          # 10 XOF/kg
        {"date": "2020-02-15", "price": 910, "unit": "L", "commodity": "Oil (palm)"},  # 1000 XOF/kg
        {"date": "2020-03-15", "price": 0},                              # invalid, removed
        {"date": "2020-04-15", "price": 200, "commodity": "Groundnuts"},  # renamed to Peanut
    ])
    df = clean(raw)

    assert len(df) == 3
    assert "pricetype" not in df.columns and "currency" not in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert set(df["commodity"]) == {"Maize", "Oil (palm)", "Peanut"}
    prices = df.set_index("commodity")["price_xof_per_kg"]
    assert prices["Maize"] == pytest.approx(10)
    assert prices["Oil (palm)"] == pytest.approx(1000)


def test_detect_shocks_flags_a_sudden_jump_only():
    months = pd.date_range("2018-01-01", periods=30, freq="MS") + pd.Timedelta(days=14)
    rng = np.random.default_rng(0)
    prices = 300 * np.exp(rng.normal(0, 0.02, len(months)).cumsum())
    prices[24] = prices[23] * 1.6  # +60% in one month
    df = pd.DataFrame({"date": months, "commodity": "Maize", "market": "Bouake",
                       "price_xof_per_kg": prices})

    shocks = detect_shocks(df)
    flagged = shocks.loc[shocks["shock"], "month"].astype(str).tolist()
    assert flagged[0] == "2020-01"
