from logging import getLogger
from textwrap import dedent
from urllib.error import HTTPError

import tradingview_screener.constants
from tradingview_screener import *
from .async_screener import Query, Scanner
from mcp import McpError
from mcp.types import Tool, TextContent

from .column_values_index import index

trading_view_scanner_query_language = dedent(f"""
The Query object represents a query that can be made to the official tradingview API, and it stores all the data as JSON internally.

Examples:

To perform a simple query all you have to do is:
```python
Query().get_scanner_data()
```
By default, the Query will select the columns: name, close, volume, market_cap_basic, but you override that

```python
Query().select('open', 'high', 'low', 'VWAP', 'MACD.macd', 'RSI', 'Price to Earnings Ratio (TTM)')
```

do some queries using the WHERE statement, select all the stocks that the close is bigger or equal than 350
```python
Query().select('close', 'volume', '52 Week High').where(Column('close') >= 350)
```

You can even use other columns in these kind of operations
```python
Query().select('close', 'VWAP').where(Column('close') >= Column('VWAP'))
```

find all the stocks that the price is between the EMA 5 and 20, and the type is a stock or fund
```python
(Query().select('close', 'volume', 'EMA5', 'EMA20', 'type')
...  .where(
...     Column('close').between(Column('EMA5'), Column('EMA20')),
...     Column('type').isin(['stock', 'fund'])
...  ))
```

There are also the ORDER BY, OFFSET, and LIMIT statements. The following query selects all the tickers with a market cap between 1M and 50M, that have a relative volume bigger than 1.2, and that the MACD is positive
```python
(Query()
...  .select('name', 'close', 'volume', 'relative_volume_10d_calc')
...  .where(
...      Column('market_cap_basic').between(1_000_000, 50_000_000),
...      Column('relative_volume_10d_calc') > 1.2,
...      Column('MACD.macd') >= Column('MACD.signal')
...  )
...  .order_by('volume', ascending=False)
...  .offset(5)
...  .limit(15))
```

A Column object represents a field in the tradingview stock screener,
and it's used in SELECT queries and WHERE queries with the `Query` object.

A `Column` supports all the comparison operations:
`<`, `<=`, `>`, `>=`, `==`, `!=`, and also other methods like `between()`, `isin()`, etc.

Examples:

Some of the operations that you can do with `Column` objects:
>>> Column('close') >= 2.5
>>> Column('close').between(2.5, 15)
>>> Column('high') > Column('VWAP')
>>> Column('close').between(Column('EMA5'), Column('EMA20'))
>>> Column('type').isin(['stock', 'fund'])
>>> Column('description').like('apple')  # the same as `description LIKE '%apple%'`

The things you **can't** do with `Column` objects:
- You can't use python arithmetic operations like `+`, `-`, `*`, `/` with `Column` objects.
That means you **CANNOT** do something like this:
```python
Column('close') + 5 # will not work
# or
Column('close') * Column('volume') # will not work
# or
Column('close') * 2 # will not work
```
                                             

This tool is useful both for scanning for symbols based on criteria, and for fundamental research on stocks.
For example, to get the last year's eps and revenue of NVDA and AMZN, you can do:

```python
(Query()
...  .select('last_annual_revenue')
...  .where(
...      Column('name').isin(['NVDA', 'AMZN'])
...  )
```
>> ticker  last_annual_eps  last_annual_revenue
0  NASDAQ:NVDA           1.1933          60922000000
1  NASDAQ:AMZN           2.8998         574785000000

""")
trading_view_name_prefix = "stock_research"
logger = getLogger(__name__)

tools = [
    Tool(
        name=f"{trading_view_name_prefix}_scan_for_stocks",
        description="Scan for stocks based on a query from the tradingview_screener library\n" + trading_view_scanner_query_language,
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "One liner python code that creates a Query object, without imports and without the get_scanner_data() call"}
            },
            "required": ["query"]
        }
    ),
    Tool(
        name=f"{trading_view_name_prefix}_scan_from_scanner",
        description="Use a scanner from the built-in scanner list",
        inputSchema={
            "type": "object",
            "properties": {
                "list_name": {
                    "type": "string",
                    "description": f"The name of the built-in scanner to use, one of: {tradingview_screener.Scanner.names()}",
                    "enum": tradingview_screener.Scanner.names()
                }
            },
            "required": ["list_name"]
        }
    ),
    Tool(
        name=f"{trading_view_name_prefix}_search_available_columns",
        description="Search for exact column names that are similar (case insensitive)"
                    " to the given query, for example: when query='Average', the tool will return all the columns that"
                    " represent averages like {'average_volume_60d_calc', 'EMA20', 'EMA10', 'SMA10', 'average_volume_30d_calc', 'ADR', 'EMA5', 'VWMA', 'HullMA9', 'EMA100', 'EMA50', 'SMA20', 'EMA30', 'average_volume_10d_calc', 'ADX', 'average_volume_90d_calc', 'SMA200', 'SMA5', 'EMA200', 'SMA30', 'ATR', 'SMA100', 'VWAP', 'SMA50'}",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The columns that match this query will be returned"}
            },
            "required": ["query"]
        }
    )
]

async def tool_handler(name: str, arguments: dict):
    if name == f"{trading_view_name_prefix}_scan_for_stocks":
        query = arguments["query"]
        try:
            query_object = eval(query)
            try:
                result = (await query_object.async_get_scanner_data())[1]
                return [
                    TextContent(type="text", text=str(result))
                ]
            except HTTPError as err:
                if "unknown field" in err.message.lower():
                    return [
                        TextContent(
                            type="text",
                            text=f"Unknown field in query: {query}, query the available columns"
                                 f" with {tools[2].name} and try again with a valid column"
                        )
                    ]
                else:
                    raise McpError(f"Error while executing query: {err}")

        except Exception as e:
            raise McpError("Error while executing query: "+ repr(e))
    elif name == f"{trading_view_name_prefix}_scan_from_scanner":
        list_name = arguments["list_name"]
        try:
            result = (await getattr(Scanner, list_name).async_get_scanner_data())[1]
            return [
                TextContent(type="text", text=str(result))
            ]
        except Exception as e:
            raise McpError("Error while executing query: "+ repr(e))
    elif name == f"{trading_view_name_prefix}_search_available_columns":
        query = arguments.get("query", "")
        if not query:
            raise McpError("The query parameter is required")

        matched_columns = index.search(query)
        if len(matched_columns) == 0:
            return [
                TextContent(type="text", text="No columns found, try a different search query")
            ]
        else:
            return [
                TextContent(type="text", text=str(matched_columns))
            ]
    else:
        raise ValueError(f"Unknown tool {name}")
