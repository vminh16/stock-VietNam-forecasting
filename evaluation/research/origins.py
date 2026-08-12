import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml


SCHEMA_VERSION = "m2_1_origin_registry_v1"


@dataclass(frozen=True)
class FoldSpec:
    fold_id: str
    start: date
    end: date


@dataclass(frozen=True)
class OriginRegistryConfig:
    schema_version: str
    dataset_id: str
    dataset_dir: Path
    universe_path: Path
    registry_path: Path
    report_dir: Path
    lookbacks: tuple
    horizon: int
    minimum_cross_section: int
    lockbox_start: date
    folds: tuple


def _as_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def load_origin_config(path):
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    folds = tuple(
        FoldSpec(
            fold_id=str(item["fold_id"]),
            start=_as_date(item["start"]),
            end=_as_date(item["end"]),
        )
        for item in raw["folds"]
    )
    config = OriginRegistryConfig(
        schema_version=str(raw["schema_version"]),
        dataset_id=str(raw["dataset_id"]),
        dataset_dir=Path(raw["dataset_dir"]),
        universe_path=Path(raw["universe_path"]),
        registry_path=Path(raw["registry_path"]),
        report_dir=Path(raw["report_dir"]),
        lookbacks=tuple(int(value) for value in raw["lookbacks"]),
        horizon=int(raw["horizon"]),
        minimum_cross_section=int(raw["minimum_cross_section"]),
        lockbox_start=_as_date(raw["lockbox_start"]),
        folds=folds,
    )
    _validate_config(config)
    return config


def _validate_config(config):
    if config.schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema version: {config.schema_version}")
    if config.lookbacks != (63, 126):
        raise ValueError("M2.1 lookbacks must be (63, 126)")
    if config.horizon != 5:
        raise ValueError("M2.1 horizon must be 5")
    if config.minimum_cross_section < 10:
        raise ValueError("minimum_cross_section must be at least 10")
    if len({fold.fold_id for fold in config.folds}) != len(config.folds):
        raise ValueError("Fold IDs must be unique")

    previous_end = None
    for fold in config.folds:
        if fold.start > fold.end:
            raise ValueError(f"Fold starts after it ends: {fold.fold_id}")
        if previous_end is not None and fold.start <= previous_end:
            raise ValueError("Folds must be increasing and non-overlapping")
        if fold.end >= config.lockbox_start:
            raise ValueError(f"Fold touches lockbox: {fold.fold_id}")
        previous_end = fold.end


def dataset_fingerprint(manifest):
    payload = {
        "dataset_id": manifest["dataset_id"],
        "policy_version": manifest["policy_version"],
        "artifact_hashes": manifest["artifact_hashes"],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
