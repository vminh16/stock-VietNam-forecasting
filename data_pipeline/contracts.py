PRICE_COLUMNS = ["open", "high", "low", "close"]
FEATURE_COLUMNS = [*PRICE_COLUMNS, "volume", "amount"]
RAW_COLUMNS = [*PRICE_COLUMNS, "volume"]
CURATED_COLUMNS = [
    "security_id", "symbol", "timestamps", "session_id", "segment_id",
    *FEATURE_COLUMNS, "amount_source",
]

CANONICAL_TIMESTAMP_HOUR = 9
PRICE_UNIT = "thousand_vnd"
PRICE_ADJUSTMENT_STATUS = "unverified_provider_history"
AMOUNT_POLICY = "derived_ohlc4_compatibility_proxy"

CONTINUITY_CANDIDATE_THRESHOLD = 0.17


def continuity_candidate_threshold(exchange):
    if exchange not in {"HOSE", "HNX", "UPCOM"}:
        raise ValueError(f"Unsupported exchange: {exchange}")
    return CONTINUITY_CANDIDATE_THRESHOLD
