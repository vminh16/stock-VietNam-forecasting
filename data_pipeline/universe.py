from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ("security_id", "symbol", "exchange", "included_as_of")
ALLOWED_EXCHANGES = {"HOSE", "HNX", "UPCOM"}


def load_universe(path, expected_size=150):
    path = Path(path)
    universe = pd.read_csv(path, dtype=str)

    missing_columns = set(REQUIRED_COLUMNS) - set(universe.columns)
    if missing_columns:
        raise ValueError(f"Universe is missing columns: {sorted(missing_columns)}")

    universe = universe.loc[:, REQUIRED_COLUMNS].copy()
    if universe.isna().any().any() or (universe == "").any().any():
        raise ValueError("Universe contains empty values")
    if len(universe) != expected_size:
        raise ValueError(f"Universe must contain exactly {expected_size} rows")
    if universe["security_id"].duplicated().any():
        raise ValueError("Universe contains duplicate security_id values")
    if universe.duplicated(["symbol", "exchange"]).any():
        raise ValueError("Universe contains duplicate symbol/exchange values")
    if not universe["symbol"].str.fullmatch(r"[A-Z0-9]{3,10}").all():
        raise ValueError("Universe symbols must be uppercase alphanumeric values")
    if not set(universe["exchange"]) <= ALLOWED_EXCHANGES:
        raise ValueError("Universe contains an unsupported exchange")

    expected_ids = universe["exchange"] + "_" + universe["symbol"]
    if not universe["security_id"].equals(expected_ids):
        raise ValueError("security_id must use the <exchange>_<symbol> format")

    included_as_of = pd.to_datetime(
        universe["included_as_of"], format="%Y-%m-%d", errors="coerce"
    )
    if included_as_of.isna().any() or included_as_of.nunique() != 1:
        raise ValueError("included_as_of must contain one valid freeze date")
    universe["included_as_of"] = included_as_of

    return universe.sort_values(["exchange", "symbol"]).reset_index(drop=True)
