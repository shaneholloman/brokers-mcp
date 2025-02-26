from datetime import datetime, timedelta

from common_lib.mcp import get_current_market_time
from pytz import timezone


def is_market_open():
    now = get_current_market_time()
    return now.weekday() < 5 and (10 <= now.hour < 16 or now.hour == 9 and now.minute >= 30)


def datetime_to_time_ago(timestamp: datetime) -> str:
    time_diff = get_current_market_time() - timestamp
    if time_diff < timedelta(minutes=1):
        time_ago_string = "just now"
    elif time_diff < timedelta(minutes=60):
        time_ago_string = f"{time_diff.seconds // 60} minute{'s' if time_diff.seconds // 60 > 1 else ''} ago"
    elif time_diff < timedelta(days=1):
        time_ago_string = f"{time_diff.seconds // 3600} hour{'s' if time_diff.seconds // 3600 > 1 else ''} ago"
    else:
        time_ago_string = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
    return time_ago_string