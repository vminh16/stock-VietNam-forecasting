import hashlib
import gzip
import io
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml
import numpy as np
import pandas as pd

from data_pipeline.crawl import sha256_file


SCHEMA_VERSION = "m2_1_origin_registry_v1"
REGISTRY_COLUMNS = [
    "schema_version",
    "dataset_fingerprint",
    "fold_id",
    "origin_id",
    "security_id",
    "symbol",
    "exchange",
    "segment_id",
    "origin_date",
    "target_start_date",
    "target_end_date",
    "row_start_l63",
    "row_start_l126",
    "row_origin",
    "row_target_start",
    "row_target_end",
]


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
    dataset_manifest_path: Path
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
        dataset_manifest_path=Path(raw["dataset_manifest_path"]),
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


def _load_dataset_inputs(config):
    manifest = json.loads(config.dataset_manifest_path.read_text(encoding="utf-8"))
    if manifest["dataset_id"] != config.dataset_id:
        raise ValueError("Dataset ID does not match origin config")

    universe = pd.read_csv(config.universe_path)
    required = {"security_id", "symbol", "exchange"}
    missing = required - set(universe.columns)
    if missing:
        raise ValueError(f"Universe is missing columns: {sorted(missing)}")
    if universe["security_id"].duplicated().any():
        raise ValueError("Universe security_id values must be unique")
    return manifest, universe.sort_values("security_id").reset_index(drop=True)


def _origin_id(fingerprint, fold_id, security_id, origin_date, horizon):
    payload = (
        f"{fingerprint}|{fold_id}|{security_id}|"
        f"{origin_date:%Y-%m-%d}|H={horizon}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_symbol(config, manifest, symbol, security_id):
    relative_path = f"symbols/{symbol}.csv"
    path = config.dataset_dir / relative_path
    expected_hash = manifest["artifact_hashes"].get(relative_path)
    if expected_hash is None or sha256_file(path) != expected_hash:
        raise ValueError(f"Curated artifact hash mismatch: {relative_path}")

    frame = pd.read_csv(path)
    required = {"security_id", "symbol", "timestamps", "session_id", "segment_id"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{symbol} is missing columns: {sorted(missing)}")
    if not frame["security_id"].eq(security_id).all():
        raise ValueError(f"security_id mismatch in {relative_path}")
    if not frame["symbol"].eq(symbol).all():
        raise ValueError(f"symbol mismatch in {relative_path}")

    frame = frame.copy()
    frame["timestamps"] = pd.to_datetime(frame["timestamps"], errors="raise")
    frame["_row"] = np.arange(len(frame), dtype=np.int64)
    return frame


def read_symbol_frame(config, manifest, symbol, security_id):
    return _read_symbol(config, manifest, symbol, security_id)


def build_common_origins(config):
    manifest, universe = _load_dataset_inputs(config)
    fingerprint = dataset_fingerprint(manifest)
    max_lookback = max(config.lookbacks)
    records = []

    for item in universe.itertuples(index=False):
        frame = _read_symbol(
            config, manifest, item.symbol, item.security_id
        )
        for segment_id, segment in frame.groupby("segment_id", sort=True):
            segment = segment.sort_values("session_id", kind="mergesort")
            if len(segment) < max_lookback + config.horizon:
                continue
            rows = segment["_row"].to_numpy(dtype=np.int64)
            dates = segment["timestamps"].dt.normalize().to_numpy()
            for position in range(max_lookback - 1, len(segment) - config.horizon):
                origin_date = pd.Timestamp(dates[position])
                target_start_date = pd.Timestamp(dates[position + 1])
                target_end_date = pd.Timestamp(dates[position + config.horizon])
                if target_end_date.date() >= config.lockbox_start:
                    continue
                fold = next(
                    (
                        candidate
                        for candidate in config.folds
                        if origin_date.date() >= candidate.start
                        and target_end_date.date() <= candidate.end
                    ),
                    None,
                )
                if fold is None:
                    continue
                records.append(
                    {
                        "schema_version": config.schema_version,
                        "dataset_fingerprint": fingerprint,
                        "fold_id": fold.fold_id,
                        "origin_id": _origin_id(
                            fingerprint,
                            fold.fold_id,
                            item.security_id,
                            origin_date,
                            config.horizon,
                        ),
                        "security_id": item.security_id,
                        "symbol": item.symbol,
                        "exchange": item.exchange,
                        "segment_id": segment_id,
                        "origin_date": origin_date,
                        "target_start_date": target_start_date,
                        "target_end_date": target_end_date,
                        "row_start_l63": rows[position - 62],
                        "row_start_l126": rows[position - 125],
                        "row_origin": rows[position],
                        "row_target_start": rows[position + 1],
                        "row_target_end": rows[position + config.horizon],
                    }
                )

    origins = pd.DataFrame(records, columns=REGISTRY_COLUMNS)
    if origins.empty:
        raise ValueError("No eligible common origins")
    date_counts = origins.groupby(["fold_id", "origin_date"])["security_id"].transform(
        "nunique"
    )
    origins = origins[date_counts >= config.minimum_cross_section]
    origins = origins.sort_values(
        ["fold_id", "origin_date", "security_id"], kind="mergesort"
    ).reset_index(drop=True)
    validate_common_origins(origins, config, manifest=manifest)
    return origins


def validate_common_origins(frame, config, manifest=None):
    if list(frame.columns) != REGISTRY_COLUMNS:
        raise ValueError("Registry columns do not match the M2.1 contract")
    if frame.empty:
        raise ValueError("Origin registry is empty")
    if frame["origin_id"].duplicated().any():
        raise ValueError("Duplicate origin_id")
    if frame.duplicated(["fold_id", "security_id", "origin_date"]).any():
        raise ValueError("Duplicate symbol-origin key")
    if not (frame["schema_version"] == config.schema_version).all():
        raise ValueError("Registry schema version mismatch")
    if not (frame["row_origin"] - frame["row_start_l63"] == 62).all():
        raise ValueError("Registry lacks exactly 63 history rows")
    if not (frame["row_origin"] - frame["row_start_l126"] == 125).all():
        raise ValueError("Registry lacks exactly 126 history rows")
    if not (frame["row_target_start"] - frame["row_origin"] == 1).all():
        raise ValueError("Target does not begin after the origin")
    if not (frame["row_target_end"] - frame["row_origin"] == config.horizon).all():
        raise ValueError("Target length does not match horizon")

    expected_order = frame.sort_values(
        ["fold_id", "origin_date", "security_id"], kind="mergesort"
    ).reset_index(drop=True)
    if not frame.reset_index(drop=True).equals(expected_order):
        raise ValueError("Registry ordering is not canonical")

    date_counts = frame.groupby(["fold_id", "origin_date"])["security_id"].nunique()
    if not date_counts.ge(config.minimum_cross_section).all():
        raise ValueError("Registered date is below minimum cross-section")

    fold_ends = {fold.fold_id: pd.Timestamp(fold.end) for fold in config.folds}
    expected_fold_end = frame["fold_id"].map(fold_ends)
    if expected_fold_end.isna().any():
        raise ValueError("Registry contains an unknown fold")
    if not (frame["target_end_date"] <= expected_fold_end).all():
        raise ValueError("Target leaves evaluation fold")
    if not (frame["target_end_date"] < pd.Timestamp(config.lockbox_start)).all():
        raise ValueError("Target touches lockbox")

    if manifest is None:
        manifest, _ = _load_dataset_inputs(config)
    fingerprint = dataset_fingerprint(manifest)
    if not frame["dataset_fingerprint"].eq(fingerprint).all():
        raise ValueError("Dataset fingerprint mismatch")

    for symbol, rows in frame.groupby("symbol", sort=False):
        security_id = rows["security_id"].iloc[0]
        source = _read_symbol(config, manifest, symbol, security_id)
        offsets = rows[
            [
                "row_start_l63",
                "row_start_l126",
                "row_origin",
                "row_target_start",
                "row_target_end",
            ]
        ].to_numpy(dtype=np.int64)
        if offsets.min() < 0 or offsets.max() >= len(source):
            raise ValueError(f"Registry row offset is out of bounds: {symbol}")
        segments = source["segment_id"].to_numpy()[offsets]
        if not (segments == segments[:, :1]).all():
            raise ValueError(f"Registry crosses a segment: {symbol}")
        source_dates = source["timestamps"].dt.normalize().to_numpy()
        if not np.array_equal(
            source_dates[offsets[:, 2]],
            rows["origin_date"].to_numpy(dtype="datetime64[ns]"),
        ):
            raise ValueError(f"Origin date does not match row offset: {symbol}")
        if not np.array_equal(
            source_dates[offsets[:, 3]],
            rows["target_start_date"].to_numpy(dtype="datetime64[ns]"),
        ):
            raise ValueError(f"Target start does not match row offset: {symbol}")
        if not np.array_equal(
            source_dates[offsets[:, 4]],
            rows["target_end_date"].to_numpy(dtype="datetime64[ns]"),
        ):
            raise ValueError(f"Target end does not match row offset: {symbol}")

        expected_ids = [
            _origin_id(
                fingerprint,
                row.fold_id,
                row.security_id,
                row.origin_date,
                config.horizon,
            )
            for row in rows.itertuples(index=False)
        ]
        if rows["origin_id"].tolist() != expected_ids:
            raise ValueError(f"Origin ID mismatch: {symbol}")


def write_registry(frame, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    output = frame.copy()
    for column in ("origin_date", "target_start_date", "target_end_date"):
        output[column] = pd.to_datetime(output[column]).dt.strftime("%Y-%m-%d")

    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                output.to_csv(text, index=False, lineterminator="\n")
    os.replace(temporary, path)
    return path
