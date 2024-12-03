import dataclasses
import json
from datetime import datetime
from typing import Callable, Any

from ib_insync import util
from mcp import Resource, Tool
from pydantic import BaseModel, AnyUrl
from pytz import timezone


class BrokerResources(BaseModel):
    host: str
    resources: list[Resource]
    handler: Callable[[AnyUrl], Any]


class BrokerTools(BaseModel):
    name_prefix: str
    tools: list[Tool]
    handler: Callable[[str, dict], Any]

def is_market_open():
    now = datetime.now(tz=timezone("US/Eastern"))
    return now.weekday() < 5 and 9 <= now.hour < 16

def unpack(obj):
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

def list_items(items):
    list_ = []
    for item in items:
        if util.isnamedtupleinstance(item):
            list_.append(unpack(item))
        elif util.is_dataclass(item):
            list_.append(dataclasses.asdict(item))
        else:
            list_.append(item)
    return json.dumps(list_, indent=2, default=str)
