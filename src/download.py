"""Download the WFP food prices dataset for Côte d'Ivoire from HDX.

    python -m src.download          # download only if the file is missing
    python -m src.download --force  # download the latest version again
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import requests

from src.config import HDX_API_URL, HDX_DATASET_ID, HDX_FILE_NAME, RAW_PATH


def find_csv_url() -> str:
    """Ask the HDX API for the current download link of the prices CSV."""
    response = requests.get(HDX_API_URL, params={"id": HDX_DATASET_ID}, timeout=60)
    response.raise_for_status()
    for resource in response.json()["result"]["resources"]:
        if resource["url"].endswith(HDX_FILE_NAME):
            return resource["url"]
    raise RuntimeError(f"{HDX_FILE_NAME} not found in HDX dataset {HDX_DATASET_ID}")


def download(path: Path = RAW_PATH, force: bool = False) -> Path:
    """Download the raw CSV to `path` (data/raw/ by default) and return the path."""
    if path.exists() and not force:
        print(f"Raw data already present: {path} (use --force to refresh)")
        return path
    url = find_csv_url()
    print(f"Downloading {url}")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    print(f"Saved {len(response.content) / 1e6:.1f} MB to {path} on {date.today()}")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="download again even if the file exists")
    download(force=parser.parse_args().force)
