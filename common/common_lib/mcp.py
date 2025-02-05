import asyncio
from datetime import datetime
from typing import Literal
from mcp.server.fastmcp import FastMCP
from mcp.server.lowlevel.server import request_ctx
import pytz

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


def get_current_market_time() -> datetime:
    request_context = request_ctx.get()
    if not hasattr(request_context.meta, "marketTime") or request_context.meta.marketTime == "realtime":
        return datetime.now(tz=pytz.timezone("US/Eastern"))
    else:
        parsed = datetime.fromisoformat(request_context.meta.marketTime).replace(tzinfo=None)
        return pytz.timezone("US/Eastern").localize(parsed)

def is_realtime() -> bool:
    request_context = request_ctx.get()
    return not hasattr(request_context.meta, "marketTime") or request_context.meta.marketTime == "realtime"

def get_thread_id() -> str:
    request_context = request_ctx.get()
    if request_context.meta is None:
        raise ValueError("No thread ID found")
    return request_context.meta.threadId
