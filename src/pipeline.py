"""Run the whole project end to end:

    python -m src.pipeline

1. download the raw data from HDX (skipped if data/raw/ already has it)
2. clean it and save data/processed/food_prices_clean.csv
3. draw the three communication charts in reports/figures/
"""

from src.cleaning import clean, load_raw, save_processed
from src.charts import make_all


def main() -> None:
    df = clean(load_raw())  # load_raw downloads the file if it is missing
    print(f"Clean data: {len(df)} rows -> {save_processed(df)}")
    for path in make_all(df):
        print(f"Chart -> {path}")


if __name__ == "__main__":
    main()
