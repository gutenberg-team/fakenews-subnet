from datetime import datetime
from typing import TYPE_CHECKING

from pytz import utc

if TYPE_CHECKING:
    import bittensor as bt

MINERS_MINIMUM_ALPHA_BASE = 100
MINERS_MINIMUM_ALPHA_ENABLE_DATE = "2025-03-11T00:00:00+00:00"
MINERS_MINIMUM_ALPHA_DAILY_INCREASE = 1476  # 7200 (total emission) * 0.41 (miners) * 0.5 (pool)


def calculate_minimum_miner_alpha(metagraph: "bt.metagraph"):

    miners_count = max(
        sum(not (n.validator_permit and n.validator_trust > 0 and n.trust == 0) for n in metagraph.neurons),
        1  # Avoid division by zero
    )

    # Calculate the minimum alpha for each miner.
    daily_miner_alpha_increase = MINERS_MINIMUM_ALPHA_DAILY_INCREASE // miners_count
    considering_days = (datetime.now(tz=utc) - datetime.fromisoformat(MINERS_MINIMUM_ALPHA_ENABLE_DATE)).days

    return MINERS_MINIMUM_ALPHA_BASE + daily_miner_alpha_increase * considering_days
