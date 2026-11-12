"""Food prices in Côte d'Ivoire: interactive dashboard.

Run from the project root:
    streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # make `src` importable

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from src.analysis import detect_shocks, monthly_series  # noqa: E402
from src.cleaning import clean, load_raw  # noqa: E402

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

st.set_page_config(page_title="Food prices in Côte d'Ivoire", layout="wide")


@st.cache_data
def get_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = clean(load_raw())
    return df, detect_shocks(df)


df, shocks = get_data()

# --- Sidebar: the user picks a commodity and a market --------------------------------
st.sidebar.header("Filters")
commodity = st.sidebar.selectbox("Commodity", sorted(df["commodity"].unique()),
                                 index=sorted(df["commodity"].unique()).index("Maize"))
counts = df.loc[df["commodity"] == commodity, "market"].value_counts()
markets = sorted(counts.index)
market = st.sidebar.selectbox("Market", markets, index=markets.index(counts.idxmax()),
                              help="Default: the market with the longest price history")
show_national = st.sidebar.checkbox("Compare with the national median", value=True)
st.sidebar.caption("Data: WFP food prices via HDX, licence CC BY-IGO. Prices in XOF per kg.")

sel = df[(df["commodity"] == commodity) & (df["market"] == market)]
series = monthly_series(sel)
s_shocks = shocks[(shocks["commodity"] == commodity) & (shocks["market"] == market) & shocks["shock"]]

st.title(f"{commodity} in {market}")
st.caption(f"{sel['admin1'].iloc[0]} region · {sel['date'].min():%b %Y} to {sel['date'].max():%b %Y} · "
           f"{len(sel)} monthly prices")

# --- Key figures ----------------------------------------------------------------------
valid = series.dropna()
latest = valid.iloc[-1]
year_ago = series.get(valid.index[-1] - 12)
national_latest = df[(df["commodity"] == commodity) & (df["date"] == sel["date"].max())]["price_xof_per_kg"].median()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest price", f"{latest:,.0f} XOF/kg", help=f"{valid.index[-1]}")
c2.metric("Change over 12 months",
          f"{(latest / year_ago - 1) * 100:+.0f}%" if pd.notna(year_ago) else "n/a")
c3.metric("vs. national median (same month)", f"{(latest / national_latest - 1) * 100:+.0f}%")
c4.metric("Price shocks detected", len(s_shocks), help="|rolling z-score| > 3 and a monthly change of at least 10%")

# --- Price over time ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 4))
ax.plot(series.index.to_timestamp(), series.values, color="#2980B9", lw=1.8, label=market)
if show_national:
    national = df[df["commodity"] == commodity].groupby("date")["price_xof_per_kg"].median()
    ax.plot(national.index, national.values, color="#999999", lw=1.2, ls="--", label="National median")
if not s_shocks.empty:
    ax.scatter(s_shocks["month"].dt.to_timestamp(), s_shocks["price"], color="#C0392B", s=45,
               zorder=3, label="Price shock")
ax.set_ylabel("XOF per kg")
ax.spines[["top", "right"]].set_visible(False)
ax.grid(alpha=0.3)
ax.legend()
st.subheader("Price over time")
st.pyplot(fig)

# --- Seasonal pattern -----------------------------------------------------------------
left, right = st.columns([3, 2])
with left:
    st.subheader("Seasonal pattern")
    trend = series.interpolate(limit=2).rolling(12, center=True, min_periods=12).mean()
    ratio = (series / trend).dropna()
    if len(ratio) >= 24:
        profile = (ratio.groupby(ratio.index.month).mean() - 1) * 100
        fig2, ax2 = plt.subplots(figsize=(7, 3.2))
        ax2.bar([MONTHS[m - 1] for m in profile.index], profile.values,
                color=["#C0392B" if v > 0 else "#27AE60" for v in profile.values])
        ax2.axhline(0, color="#555555", lw=0.8)
        ax2.set_ylabel("% vs. trend")
        ax2.spines[["top", "right"]].set_visible(False)
        st.pyplot(fig2)
        st.caption("Average gap between the price and its 12-month moving average, by calendar month.")
    else:
        st.info("Not enough continuous data (at least 3 years) to estimate a seasonal pattern.")

with right:
    st.subheader("Detected shocks")
    if s_shocks.empty:
        st.write("No price shock detected for this series.")
    else:
        table = pd.DataFrame({
            "Month": s_shocks["month"].astype(str),
            "Price (XOF/kg)": s_shocks["price"].round(0).astype(int),
            "Monthly change": ((np.exp(s_shocks["change"]) - 1) * 100).map("{:+.0f}%".format),
            "z-score": s_shocks["z"].round(1),
        })
        st.dataframe(table, hide_index=True, width="stretch")
