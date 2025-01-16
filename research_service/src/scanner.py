from textwrap import dedent

# Documentation for the query language
QUERY_LANGUAGE_DOCS = dedent("""
The Query object represents a query that can be made to the official tradingview API, and it stores all the data as JSON internally.
IMPORTANT NOTE:
The "name" column refers to the ticker symbol, like "AAPL" or "MSFT".

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
                             
All supported Column operations:
* > 
* >= 
* < 
* <= 
* == 
* != 
* between
Example:
>>> Column('close').between(Column('EMA200'), Column('EMA50'))
* not_between
Example:
>>> Column('close').not_between(Column('EMA200'), Column('EMA50'))
* isin
Example:
>>> Column('name').isin(["AAPL", "MSFT"]) # get AAPL and MSFT tickers
* not_in
Example:
>>> Column('name').not_in(["AAPL", "MSFT"]) # get all tickers except AAPL and MSFT
* has
Example:
>>> Column('typespecs').has(["common"]) # used when the column value is a list
* has_none_of               
* above_pct
Examples:
    The closing price is higher than the VWAP by more than 3%
    >>> Column('close').above_pct(Column('VWAP'), 1.03)

    closing price is above the 52-week-low by more than 150%
    >>> Column('close').above_pct(Column('price_52_week_low'), 2.5)
* below_pct
Examples:
    The closing price is lower than the VWAP by 3% or more
    >>> Column('close').below_pct('VWAP', 1.03)                      
* between_pct
Examples:
    The percentage change between the Close and the EMA is between 20% and 50%
    >>> Column('close').between_pct('EMA200', 1.2, 1.5)
* not_between_pct
Examples:
    The percentage change between the Close and the EMA is between 20% and 50%
    >>> Column('close').not_between_pct('EMA200', 1.2, 1.5)
* like
Examples:
    The stock description contains "Crypto"
    >>> Column('description').like("Crypto")
""")
