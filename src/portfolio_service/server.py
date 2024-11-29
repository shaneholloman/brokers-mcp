import logging

import anyio
import dotenv
dotenv.load_dotenv()
from mcp import Resource, Tool
from mcp.server import Server
from pydantic import AnyUrl

from .brokers import tradestation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("portfolio-service")


def main():
    import mcp.server.stdio

    server = Server("portfolio-service")

    @server.list_resources()
    async def list_all_resources() -> list[Resource]:
        return [
            *tradestation.resources.resources
        ]

    @server.list_tools()
    async def list_all_tools() -> list[Tool]:
        return [
            *tradestation.tools.tools
        ]

    @server.read_resource()
    async def read_resource(uri: AnyUrl):
        if uri.host == tradestation.resources.host:
            return await tradestation.resources.handler(uri)
        else:
            raise ValueError(f"Unknown resource host: {uri.host}, supported hosts: {tradestation.resources.host}")

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name.startswith(tradestation.tools.name_prefix):
            return await tradestation.tools.handler(name, arguments)
        else:
            raise ValueError(f"Unknown tool name: {name}, supported prefix: {tradestation.tools.name_prefix}")

    async def arun():
        # Run the server using stdin/stdout streams
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    anyio.run(arun)
    return 0