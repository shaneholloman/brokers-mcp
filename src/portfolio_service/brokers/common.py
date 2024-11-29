from datetime import datetime
from typing import Callable, Any

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