from logging import getLogger
from urllib.error import HTTPError
from mcp.server.fastmcp import FastMCP
import tradingview_screener
from tradingview_screener import *
from async_screener import Query, Scanner
from column_values_index import index
from scanner import QUERY_LANGUAGE_DOCS
import traceback


logger = getLogger(__name__)

mcp = FastMCP("Research Service")

@mcp.tool(
    name="scan_from_scanner",
    description=f"""Use a scanner from the built-in scanner list.

Args:
    list_name: Name of the built-in scanner to use

Returns:
    str: Scanner results as a string

Available lists: {tradingview_screener.Scanner.names()}"""
)
async def scan_from_scanner(list_name: str) -> str:
    try:
        result = (await getattr(Scanner, list_name).async_get_scanner_data())[1]
        return str(result)
    except Exception as e:
        logger.error("Error while executing query: %s\nStack trace: %s", repr(e), traceback.format_exc())
        raise ValueError("Error while executing query: " + repr(e))

@mcp.tool(name="search_available_columns")
async def search_available_columns(query: str) -> str:
    """Search for columns that match the given query.
    For example: when query='Average', the tool will return all the columns that
    represent averages like {'average_volume_60d_calc', 'EMA20', 'EMA10', 'SMA10', etc.}

    Args:
        query: Search term to find matching column names

    Returns:
        str: Set of matching column names as a string
    """
    if not query:
        raise ValueError("The query parameter is required")

    matched_columns = index.search(query)
    if len(matched_columns) == 0:
        return "No columns found, try a different search query"
    else:
        return str(matched_columns)


@mcp.tool(
    name="scan_for_stocks",
    description=(
        "Scan for stocks based on a query from the tradingview_screener library"
        "Args: query: Query string in tradingview_screener format to filter stocks"
        "Returns: str: Scanner results as a string"
        f"{QUERY_LANGUAGE_DOCS}"
    )
)
async def scan_for_stocks(query: str) -> str:
    try:
        query_object = eval(query)
        try:
            result = (await query_object.async_get_scanner_data())[1]
            return str(result)
        except HTTPError as err:
            if "unknown field" in err.message.lower():
                return (f"Unknown field in query: {query}, query the available columns"
                       f" with search_available_columns and try again with a valid column")
            else:
                logger.error("Error while executing query: %s\nStack trace: %s", repr(err), traceback.format_exc())
                raise ValueError(f"Error while executing query: {err}")
    except Exception as e:
        logger.error("Error while executing query: %s\nStack trace: %s", repr(e), traceback.format_exc())
        raise ValueError("Error while executing query: " + repr(e))

if __name__ == "__main__":
    mcp.run(transport="sse")
    