# Data

> **No raw data is committed to this repository.** The raw file is downloaded by a script
> (`python -m src.download`) and ignored by git. Only this documentation is tracked.

## Source

| | |
|---|---|
| **Dataset** | [Côte d'Ivoire - Food Prices](https://data.humdata.org/dataset/wfp-food-prices-for-cote-d-ivoire) |
| **Publisher** | WFP - World Food Programme, on HDX (Humanitarian Data Exchange) |
| **File** | `wfp_food_prices_civ.csv` |
| **Licence** | [Creative Commons Attribution for Intergovernmental Organisations (CC BY-IGO 3.0)](http://creativecommons.org/licenses/by/3.0/igo/legalcode) |
| **Download date** | 4 November 2026 (snapshot used for all results in this repository) |
| **Update frequency** | Monthly (WFP updates the file on HDX) |

**Credit:** *World Food Programme (WFP), Côte d'Ivoire - Food Prices, Humanitarian Data Exchange (HDX), CC BY-IGO.*
The licence allows reuse, including commercial reuse, provided the source is credited.

## Content of the snapshot

- **10,992 rows**, one row = one monthly retail price for one product in one market.
- **Period:** January 2005 to September 2026 (monthly; the day is always the 15th by convention).
- **17 markets** in 9 regions, **27 products** (cereals, tubers, rice, fish, meat, oils, pulses, cocoa, fuel...).
- **Currency:** XOF (CFA franc), also converted to USD by WFP (`usdprice`).
- **Units:** `KG` (10,504 rows) or `L` (488 rows: palm oil, vegetable oil, petrol).
- **No missing values and no duplicate rows.**

| Column | Meaning |
|---|---|
| `date` | Month of the price |
| `admin1`, `admin2` | Region and sub-region of the market |
| `market`, `market_id` | Market name and WFP identifier |
| `latitude`, `longitude` | Market coordinates |
| `category`, `commodity`, `commodity_id` | Product family, product name, WFP identifier |
| `unit` | Unit of the price (`KG` or `L`) |
| `priceflag` | `actual` = observed price, `aggregate` = computed by WFP from several readings |
| `pricetype` | Always `Retail` |
| `currency` | Always `XOF` |
| `price`, `usdprice` | Price per unit in XOF and in USD |

## Known data issues (handled in `src/cleaning.py`)

- **Markets enter and leave the panel** (e.g. Bouaké stops in 2014, Korhogo starts in 2016, five markets only start in 2026), so national averages over time mix different markets.
- **Abidjan has only one market** (Adjamé), observed from 2011 to 2021.
- **Two names for one product:** `Groundnuts` and `Peanut` never overlap in the same market and month and have similar prices; they are merged.
- **Prices per litre** are converted to XOF/kg with approximate densities (palm oil 0.91, vegetable oil 0.92, petrol 0.74 kg/L).
- **38% of prices are `aggregate`** (computed by WFP), not directly observed.

## Folder layout

```text
data/
├── raw/          # wfp_food_prices_civ.csv, downloaded by src/download.py (git-ignored)
└── processed/    # food_prices_clean.csv, written by src/pipeline.py (git-ignored)
```

To get the latest version of the file instead of the existing local copy:

```bash
python -m src.download --force
```

Note that newer versions may slightly change the figures reported in this repository.
