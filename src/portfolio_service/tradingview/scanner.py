import difflib
import random
import re
from logging import getLogger
from textwrap import dedent
from urllib.error import HTTPError

import tradingview_screener.constants
from tradingview_screener import *
from mcp import McpError
from mcp.types import Tool, TextContent

trading_view_scanner_query_language = dedent(f"""
The Query object represents a query that can be made to the official tradingview API, and it stores all the data as JSON internally.

Examples:

To perform a simple query all you have to do is:
```python
Query().get_scanner_data()
```
By default, the Query will select the columns: name, close, volume, market_cap_basic, but you override that

```python
(Query().select('open', 'high', 'low', 'VWAP', 'MACD.macd', 'RSI', 'Price to Earnings Ratio (TTM)').get_scanner_data())
```

Now let's do some queries using the WHERE statement, select all the stocks that the close is bigger or equal than 350
```python
(Query()
...  .select('close', 'volume', '52 Week High')
...  .where(Column('close') >= 350)
...  .get_scanner_data())
```

You can even use other columns in these kind of operations
```python
(Query()
...  .select('close', 'VWAP')
...  .where(Column('close') >= Column('VWAP'))
...  .get_scanner_data())
```

Let's find all the stocks that the price is between the EMA 5 and 20, and the type is a stock or fund
```python
(Query()
...  .select('close', 'volume', 'EMA5', 'EMA20', 'type')
...  .where(
...     Column('close').between(Column('EMA5'), Column('EMA20')),
...     Column('type').isin(['stock', 'fund'])
...  )
...  .get_scanner_data())
```

There are also the ORDER BY, OFFSET, and LIMIT statements. Let's select all the tickers with a market cap between 1M and 50M, that have a relative volume bigger than 1.2, and that the MACD is positive
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
...  .limit(15)
...  .get_scanner_data())
```
This is a sample of the list of columns that can be queried in the scanner, however there are over 3000 columns available and you can use any of them in your queries.:
{','.join(random.sample([c for c in tradingview_screener.constants.COLUMNS.values()], 100))}
""")
trading_view_name_prefix = "tradingview"
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
    )
]

async def tool_handler(name: str, arguments: dict):
    if name == f"{trading_view_name_prefix}_scan_for_stocks":
        query = arguments["query"]
        try:
            query_object = eval(query)
            try:
                result = query_object.get_scanner_data()[1]
                return [
                    TextContent(type="text", text=str(result))
                ]
            except HTTPError as err:
                logger.error(f"Error while executing query: {err}")
                if "Unknown field" in str(err):
                    field_extract = re.compile("(?<=Unknown field \\\")([^\\\"]*)(?=\\\")")
                    wrong_field = field_extract.search(str(err)).group(0)
                    logger.error(wrong_field)
                    return [
                        TextContent(
                            type="text",
                            text=f"Unknown field in query: {wrong_field}, did you mean: {difflib.get_close_matches(wrong_field, tradingview_screener.constants.COLUMNS.values())}"
                        )
                    ]
                else:
                    raise McpError(f"Error while executing query: {err}")


        except Exception as e:
            logger.error("Error while executing query: "+ repr(e))
            raise McpError("Error while executing query: "+ repr(e))
    elif name == f"{trading_view_name_prefix}_scan_from_scanner":
        list_name = arguments["list_name"]
        try:
            result = getattr(tradingview_screener.Scanner, list_name).get_scanner_data()[1]
            return [
                TextContent(type="text", text=str(result))
            ]
        except Exception as e:
            logger.error("Error while executing query: "+ repr(e))
            raise McpError("Error while executing query: "+ repr(e))
    else:
        raise ValueError(f"Unknown tool {name}")
