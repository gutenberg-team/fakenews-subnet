from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bittensor as bt

MINERS_MINIMUM_ALPHA_BASE = 150
MINERS_MINIMUM_ALPHA_ENABLE_DATE = "2025-03-20T00:00:00+00:00"
MINERS_MINIMUM_ALPHA_DAILY_INCREASE = 6


def calculate_minimum_miner_alpha() -> int:
    considering_days = (datetime.now(tz=timezone.utc) - datetime.fromisoformat(MINERS_MINIMUM_ALPHA_ENABLE_DATE)).days
    return MINERS_MINIMUM_ALPHA_BASE + MINERS_MINIMUM_ALPHA_DAILY_INCREASE * considering_days
