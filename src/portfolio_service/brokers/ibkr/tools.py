from logging import getLogger

from .common import ibkr_tool_prefix
from .tool_types import market_data, orders, news, options
from ..common import BrokerTools

logger = getLogger(__name__)

async def handle_tool_call(name: str, arguments: dict):
    if any([name == tool.name for tool in market_data.tools]):
        return await market_data.handler(name, arguments)
    elif any([name == tool.name for tool in orders.tools]):
        return await orders.handler(name, arguments)
    elif any([name == tool.name for tool in news.tools]):
        return await news.handler(name, arguments)
    elif any([name == tool.name for tool in options.tools]):
        return await options.handler(name, arguments)
    else:
        raise ValueError(f"Unknown tool name: {name}")

tools = BrokerTools(
    name_prefix=ibkr_tool_prefix,
    tools=options.tools + market_data.tools + orders.tools + news.tools,
    handler=handle_tool_call
)
