import dataclasses
import json
from datetime import datetime, timedelta
from numbers import Number
from typing import Callable, Any

from ib_insync import util
from mcp import Resource, Tool
from pydantic import BaseModel, AnyUrl
from pytz import timezone


class BrokerResources(BaseModel):
    resources: list[Resource]
    handler: Callable[[AnyUrl], Any]


class BrokerTools(BaseModel):
    name_prefix: str
    tools: list[Tool]
    handler: Callable[[str, dict], Any]

def is_market_open():
    now = datetime.now(tz=timezone("US/Eastern"))
    return now.weekday() < 5 and (10 <= now.hour < 16 or now.hour == 9 and now.minute >= 30)

def unpack(obj) -> dict:
    if isinstance(obj, dict):
        return {key: unpack(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [unpack(value) for value in obj]
    elif util.isnamedtupleinstance(obj):
        return {key: unpack(value) for key, value in obj._asdict().items()}
    elif isinstance(obj, tuple):
        return tuple(unpack(value) for value in obj)
    elif util.is_dataclass(obj):
        return dataclasses.asdict(obj)
    else:
        return obj

def list_items(items, remove_falsy_values=False):
    list_ = []
    for item in items:
        if util.isnamedtupleinstance(item):
            list_.append(unpack(item))
        elif util.is_dataclass(item):
            list_.append(dataclasses.asdict(item))
        else:
            list_.append(item)

    if remove_falsy_values:
        list_ = _remove_falsy_values(list_)

    return json.dumps(list_, indent=2, default=str)

def _remove_falsy_values(item):
    if isinstance(item, dict):
        return {k: _remove_falsy_values(v) for k, v in item.items() if is_truthy(v)}
    elif isinstance(item, list):
        return [_remove_falsy_values(v) for v in item if is_truthy(v)]
    else:
        return item

def is_truthy(item):
    if isinstance(item, Number):
        return item > 0 and item < 1e100
    else:
        return bool(item)

def datetime_to_time_ago(timestamp: datetime) -> str:
    time_diff = datetime.now(tz=timestamp.tzinfo) - timestamp
    if time_diff < timedelta(minutes=1):
        time_ago_string = "just now"
    elif time_diff < timedelta(minutes=60):
        time_ago_string = f"{time_diff.seconds // 60} minute{'s' if time_diff.seconds // 60 > 1 else ''} ago"
    elif time_diff < timedelta(days=1):
        time_ago_string = f"{time_diff.seconds // 3600} hour{'s' if time_diff.seconds // 3600 > 1 else ''} ago"
    else:
        time_ago_string = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
    return time_ago_string