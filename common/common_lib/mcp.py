import asyncio
from typing import Literal
from mcp.server.fastmcp import FastMCP

class AsyncioFastMCP(FastMCP):
    def run(self, transport: Literal["stdio", "sse"] = "stdio") -> None:
        """Run the FastMCP server. Note this is a synchronous function.

        Args:
            transport: Transport protocol to use ("stdio" or "sse")
        """
        if transport == "stdio":
            asyncio.run(self.run_stdio_async())
        elif transport == "sse":
            asyncio.run(self.run_sse_async())
        else:
            raise ValueError(f"Invalid transport: {transport}")
