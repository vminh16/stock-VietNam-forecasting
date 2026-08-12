from pathlib import Path

import pandas as pd
import pytest

from data_pipeline.universe import load_universe


UNIVERSE_PATH = Path("data_pipeline/universe_150.csv")
BASELINE_SYMBOLS = {path.stem for path in Path("data_cleaned").glob("*.csv")}


def test_vn150_universe_contract():
    universe = load_universe(UNIVERSE_PATH)

    assert len(universe) == 150
    assert universe["security_id"].is_unique
    assert not universe.duplicated(["symbol", "exchange"]).any()
    assert set(universe["exchange"]) == {"HOSE", "HNX", "UPCOM"}
    assert universe["included_as_of"].nunique() == 1
    assert str(universe["included_as_of"].iloc[0].date()) == "2026-08-09"
    assert BASELINE_SYMBOLS <= set(universe["symbol"])


@pytest.mark.parametrize(
    "column,value",
    [
        ("symbol", "fpt"),
        ("exchange", "NYSE"),
        ("included_as_of", "not-a-date"),
    ],
)
def test_universe_rejects_invalid_values(tmp_path, column, value):
    universe = pd.read_csv(UNIVERSE_PATH)
    universe.loc[0, column] = value
    path = tmp_path / "universe.csv"
    universe.to_csv(path, index=False)

    with pytest.raises(ValueError):
        load_universe(path)


def test_universe_rejects_duplicate_security_id(tmp_path):
    universe = pd.read_csv(UNIVERSE_PATH)
    universe.loc[1, "security_id"] = universe.loc[0, "security_id"]
    path = tmp_path / "universe.csv"
    universe.to_csv(path, index=False)

    with pytest.raises(ValueError, match="security_id"):
        load_universe(path)
