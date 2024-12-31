from logging import getLogger

from .common import ibkr_tool_prefix
from .tool_types import orders, news, options
from ..common import BrokerTools

logger = getLogger(__name__)

async def handle_tool_call(name: str, arguments: dict):
    if any([name == tool.name for tool in orders.tools]):
        return await orders.handler(name, arguments)
    elif any([name == tool.name for tool in news.tools]):
        return await news.handler(name, arguments)
    elif any([name == tool.name for tool in options.tools]):
        return await options.handler(name, arguments)
    else:
        raise ValueError(f"Unknown tool name: {name}")

tools = BrokerTools(
    name_prefix=ibkr_tool_prefix,
    tools=options.tools + orders.tools + news.tools,
    handler=handle_tool_call
)
