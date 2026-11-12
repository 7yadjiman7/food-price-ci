"""Project paths and constants. All paths are relative to the project root,
so the code runs on any machine after `git clone`."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_PATH = RAW_DIR / "wfp_food_prices_civ.csv"
PROCESSED_PATH = PROCESSED_DIR / "food_prices_clean.csv"

REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# HDX (Humanitarian Data Exchange) dataset published by WFP.
HDX_DATASET_ID = "wfp-food-prices-for-cote-d-ivoire"
HDX_API_URL = "https://data.humdata.org/api/3/action/package_show"
HDX_FILE_NAME = "wfp_food_prices_civ.csv"

# Staple foods studied in the analysis.
STAPLES = [
    "Maize", "Cornstarch",
    "Rice (local)", "Rice (denikassia, imported)", "Rice (imported)",
    "Cassava (fresh)", "Cassava meal (attieke)",
    "Yam (florido)", "Yam", "Plantains",
    "Beans (niebe)", "Peanut", "Oil (palm)",
]
