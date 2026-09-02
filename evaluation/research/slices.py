import hashlib

import numpy as np
import pandas as pd


# Locked M2.6 conventions:
# - `symbol_group` is a salted-hash partition of security_id. It never reads
#   prices, returns, or results, so an unseen-symbol holdout cannot be chosen
#   after seeing which symbols a model happens to rank well.
# - `liquidity_tier` is assigned inside each evaluation date, so a tier keeps a
#   stable share of the cross-section instead of drifting with market growth.
#   `tier_0` is the most liquid tier.
# - Liquidity is the median traded `amount` over the lookback sessions ending at
#   the origin, inclusive. It reads no session after the origin.
SCHEMA_VERSION = "m2_6_origin_slices_v1"
SLICE_KEYS = ("symbol_group", "liquidity_tier")
LIQUIDITY_LOOKBACK = 63

SLICE_COLUMNS = [
    "schema_version",
    "fold_id",
    "origin_id",
    "security_id",
    "symbol",
    "origin_date",
    "liquidity_value",
    "liquidity_tier",
    "symbol_group",
]


def assign_symbol_groups(security_ids, group_count, salt):
    """Partition symbols by salted hash so the split cannot depend on results."""
    if group_count < 2:
        raise ValueError("group_count must be at least 2")
    groups = {}
    for security_id in sorted({str(value) for value in security_ids}):
        digest = hashlib.sha256(f"{salt}|{security_id}".encode("utf-8")).digest()
        index = int.from_bytes(digest[:8], "big") % group_count
        groups[security_id] = f"group_{index}"
    return groups


def trailing_liquidity(values, row_origin, lookback=LIQUIDITY_LOOKBACK):
    """Median traded amount over the lookback sessions ending at the origin."""
    start = row_origin - lookback + 1
    if start < 0:
        raise ValueError("Liquidity lookback runs before the series start")
    window = np.asarray(values, dtype=np.float64)[start : row_origin + 1]
    if window.size != lookback:
        raise ValueError("Liquidity window is incomplete")
    if not np.isfinite(window).all():
        raise ValueError("Liquidity window contains non-finite values")
    return float(np.median(window))


def liquidity_tiers(frame, tier_count):
    """Rank each date's cross-section into balanced tiers, tier_0 most liquid."""
    if tier_count < 2:
        raise ValueError("tier_count must be at least 2")
    labels = pd.Series(index=frame.index, dtype=object)
    for _, day in frame.groupby(["fold_id", "origin_date"], sort=False):
        if len(day) < tier_count:
            raise ValueError("An evaluation date holds fewer origins than tiers")
        ordered = day.sort_values(
            ["liquidity_value", "security_id"],
            ascending=[False, True],
            kind="mergesort",
        )
        position = np.arange(len(ordered))
        labels.loc[ordered.index] = [
            f"tier_{value}" for value in position * tier_count // len(ordered)
        ]
    return labels
