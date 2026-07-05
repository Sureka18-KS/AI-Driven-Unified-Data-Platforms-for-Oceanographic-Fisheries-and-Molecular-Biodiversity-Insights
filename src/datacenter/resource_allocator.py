# OPT-3: Seasonal GPU Pre-Scaling for the Indian Ocean
from datetime import datetime


# Indian Ocean monsoon calendar
MONSOON_SCHEDULE = {
    6: {"gpus": 8, "strategy": "monsoon-peak"},
    7: {"gpus": 8, "strategy": "monsoon-peak"},
    8: {"gpus": 8, "strategy": "monsoon-peak"},
    9: {"gpus": 6, "strategy": "monsoon-retreat"},
    10: {"gpus": 4, "strategy": "inter-monsoon"},
    11: {"gpus": 4, "strategy": "inter-monsoon"},
    12: {"gpus": 4, "strategy": "inter-monsoon"},
    1: {"gpus": 3, "strategy": "winter-baseline"},
    2: {"gpus": 3, "strategy": "winter-baseline"},
    3: {"gpus": 4, "strategy": "pre-monsoon"},
    4: {"gpus": 5, "strategy": "pre-monsoon"},
    5: {"gpus": 6, "strategy": "monsoon-onset"},
}


def prescale_resources(dt: datetime) -> dict:
    """
    OPT-3: Return pre-scaled GPU allocation for the given month.
    Called at the start of each 6-hourly cycle.
    """
    month = dt.month
    return MONSOON_SCHEDULE.get(month, {"gpus": 4, "strategy": "default"})
