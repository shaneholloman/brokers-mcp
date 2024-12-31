import logging
import dotenv

dotenv.load_dotenv()
import nest_asyncio
nest_asyncio.apply()
from mcp import Resource, Tool
from mcp.server import Server
from mcp.server.stdio import stdio_server

from pydantic import AnyUrl
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("portfolio-service")
from .brokers import ibkr, tradestation
from .tradingview import scanner



server = Server("portfolio-service")

@server.list_resources()
async def list_all_resources() -> list[Resource]:
    return [
        *ibkr.resources.resources,
    ]

@server.list_tools()
async def list_all_tools() -> list[Tool]:
    return [
        *ibkr.tools.tools,
        *tradestation.tools.tools,
        *scanner.tools,
    ]

@server.read_resource()
async def read_resource(uri: AnyUrl):
    return await ibkr.resources.handler(uri)

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name.startswith(ibkr.tools.name_prefix):
        return await ibkr.tools.handler(name, arguments)
    elif name.startswith(tradestation.tools.name_prefix):
        return await tradestation.tools.handler(name, arguments)
    elif name.startswith(scanner.trading_view_name_prefix):
        return await scanner.tool_handler(name, arguments)
    else:
        raise ValueError(f"Unknown tool name: {name}, supported prefix: {tradestation.tools.name_prefix}")

async def main():
    # Run the server using stdin/stdout streams
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )
    ibkr.ib.disconnect()