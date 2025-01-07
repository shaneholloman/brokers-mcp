from logging import getLogger
from urllib.error import HTTPError
from mcp.server.fastmcp import FastMCP
import tradingview_screener.constants
from tradingview_screener import *
from research_service.tradingview.async_screener import Query, Scanner

from research_service.tradingview.column_values_index import index
from research_service.tradingview.scanner import QUERY_LANGUAGE_DOCS

logger = getLogger(__name__)

mcp = FastMCP("Research Service")

@mcp.tool()
async def scan_from_scanner(list_name: str) -> str:
    """Use a scanner from the built-in scanner list.

    Args:
        list_name: Name of the built-in scanner to use

    Returns:
        str: Scanner results as a string

    Available lists: """ + str(tradingview_screener.Scanner.names())
    try:
        result = (await getattr(Scanner, list_name).async_get_scanner_data())[1]
        return str(result)
    except Exception as e:
        raise ValueError("Error while executing query: " + repr(e))

@mcp.tool()
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


@mcp.tool()
async def scan_for_stocks(query: str) -> str:
    f"""Scan for stocks based on a query from the tradingview_screener library

    Args:
        query: Query string in tradingview_screener format to filter stocks

    Returns:
        str: Scanner results as a string

{QUERY_LANGUAGE_DOCS}"""
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
                raise ValueError(f"Error while executing query: {err}")
    except Exception as e:
        raise ValueError("Error while executing query: " + repr(e))
    