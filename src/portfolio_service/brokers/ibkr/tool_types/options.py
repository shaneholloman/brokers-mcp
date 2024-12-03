from mcp import Tool

from ..common import ibkr_tool_prefix

tools = [
    Tool(
        name=f"{ibkr_tool_prefix}_get_option_expirations",
        description="Get the expiration dates for options of an underlying",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "The symbol of the underlying"
                },
                "type": {
                    "type": "string",
                    "description": "The type of the underlying, either 'stock', 'index', or 'future'. Default is 'stock'",
                    "enum": ["stock", "index", "future"],
                    "default": "stock"
                }
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name=f"{ibkr_tool_prefix}_read_option_chain",
        description="Read the option chain for an underlying at a specific expiration date",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "The symbol of the underlying"},
                "expiration": {"type": "string", "description": "The expiration date of the options, format: 'YYYYMMDD'"},
                "type": {"type": "string", "description": "The type of the underlying, either 'stock', 'index', or 'future'. Default is 'stock'"},
            },
            "required": ["symbol", "expiration"]
        }
    )
]

def handler(name, arguments):
    if name == f"{ibkr_tool_prefix}_get_option_expirations":
        return get_option_expirations(arguments)
    elif name == f"{ibkr_tool_prefix}_read_option_chain":
        return read_option_chain(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")