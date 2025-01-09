import pandas as pd
import aiohttp
import tradingview_screener as tvs
from tradingview_screener.constants import COLUMNS, MARKETS, HEADERS, URL

DEFAULT_COLUMNS = ['name', 'close', 'volume', 'market_cap_basic']  # for the scanners


class Query(tvs.Query):
    async def async_get_scanner_data(self, **kwargs):
        # Set default headers and timeout if not provided
        kwargs.setdefault('headers', HEADERS)
        timeout_value = kwargs.pop('timeout', 20)

        # Create an aiohttp ClientSession to handle async requests
        timeout = aiohttp.ClientTimeout(total=timeout_value)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Perform the POST request asynchronously
            async with session.post(self.url, json=self.query, **kwargs) as r:
                if r.status >= 400:
                    # If there’s an HTTP error, attach body text for better debugging
                    body_text = await r.text()
                    reason = f"{r.reason}\n Body: {body_text}\n"

                    # Raise a ClientResponseError which includes the status, reason, etc.
                    raise aiohttp.ClientResponseError(
                        request_info=r.request_info,
                        history=r.history,
                        status=r.status,
                        message=reason,
                    )

                # If the request is successful, parse the JSON response
                json_obj = await r.json()
                rows_count = json_obj['totalCount']
                data = json_obj['data']

                # Construct a DataFrame from the returned data
                df = pd.DataFrame(
                    data=([row['s'], *row['d']] for row in data),
                    columns=['ticker', *self.query.get('columns', ())],
                )
                return rows_count, df

class Scanner:
    premarket_gainers = (
        Query()
        .select(*DEFAULT_COLUMNS, 'premarket_change', 'premarket_change_abs', 'premarket_volume')
        .order_by('premarket_change', ascending=False)
    )
    premarket_losers = (
        Query()
        .select(*DEFAULT_COLUMNS, 'premarket_change', 'premarket_change_abs', 'premarket_volume')
        .order_by('premarket_change', ascending=True)
    )
    premarket_most_active = (
        Query()
        .select(*DEFAULT_COLUMNS, 'premarket_change', 'premarket_change_abs', 'premarket_volume')
        .order_by('premarket_volume', ascending=False)
    )
    premarket_gappers = (
        Query()
        .select(*DEFAULT_COLUMNS, 'premarket_change', 'premarket_change_abs', 'premarket_volume')
        .order_by('premarket_gap', ascending=False)
    )

    postmarket_gainers = (
        Query()
        .select(*DEFAULT_COLUMNS, 'postmarket_change', 'postmarket_change_abs', 'postmarket_volume')
        .order_by('postmarket_change', ascending=False)
    )
    postmarket_losers = (
        Query()
        .select(*DEFAULT_COLUMNS, 'postmarket_change', 'postmarket_change_abs', 'postmarket_volume')
        .order_by('postmarket_change', ascending=True)
    )
    postmarket_most_active = (
        Query()
        .select(*DEFAULT_COLUMNS, 'postmarket_change', 'postmarket_change_abs', 'postmarket_volume')
        .order_by('postmarket_volume', ascending=False)
    )

    @classmethod
    def names(cls) -> list[str]:
        return [x for x in cls.__dict__.keys() if not x.startswith('_') and x != 'names']