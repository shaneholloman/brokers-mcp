import asyncio
import datetime
import json
import logging
import os

from dotenv import load_dotenv

from src.common import is_market_open

load_dotenv()

import time
from datetime import datetime
from datetime import timedelta
from enum import Enum
from functools import wraps
from typing import Iterator, Optional

import aiohttp
import numpy as np
import pandas as pd
import pytz
import requests
from aiohttp import ClientResponseError
from pandas import Timedelta
from pydantic import BaseModel
from requests import HTTPError
from retry import retry


class OrderStatus(Enum):
    PENDING = 0
    ACTIVE = 1
    FILLED = 2
    CANCELLED = 3
    REJECTED = 4

logger = logging.getLogger(__name__)


def refresh_token(func):
    @wraps(func)
    async def async_wrapper(self, *args, **kwargs):
        self._refresh_access_token()
        return await func(self, *args, **kwargs)

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self._refresh_access_token()
        return func(self, *args, **kwargs)

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return wrapper


def parse_order_status(status: str):
    if status == "FLL":
        return OrderStatus.FILLED
    if status == "ACK" or status == "OPN" or status == "DON":
        return OrderStatus.ACTIVE
    if status == "CAN":
        return OrderStatus.CANCELLED
    else:
        return OrderStatus.REJECTED

class TemporaryError(Exception):
    pass


class Quote(BaseModel):
    Symbol: str
    Open: float
    PreviousClose: float
    Last: float
    Ask: float
    AskSize: int
    Bid: float
    BidSize: int
    NetChange: float
    NetChangePct: float
    High52Week: float
    High52WeekTimestamp: datetime
    Low52Week: float
    Low52WeekTimestamp: datetime
    Volume: int
    PreviousVolume: int
    Close: float
    DailyOpenInterest: int
    TradeTime: datetime
    TickSizeTier: int


class CreateOrder(BaseModel):
    AccountID: str = os.getenv("TS_ACCOUNT_ID")
    Symbol: str
    Quantity: int
    OrderType: str
    TimeInForce: dict
    TradeAction: str
    OSOs: Optional[list["CreateOrder"]] = None
    LimitPrice: Optional[float] = None
    StopPrice: Optional[float] = None

    def to_payload(self):
        pl = {
            "AccountID": self.AccountID,
            "Symbol": self.Symbol,
            "Quantity": str(self.Quantity),
            "OrderType": self.OrderType,
            "TimeInForce": self.TimeInForce,
            "TradeAction": self.TradeAction,
        }
        if self.LimitPrice:
            pl["LimitPrice"] = str(self.LimitPrice)
        if self.StopPrice:
            pl["StopPrice"] = str(self.StopPrice)
        if self.OSOs:
            pl["OSOs"] = [
                {
                    "Orders": [o.to_payload() for o in self.OSOs],
                    "Type": "OCO"
                }
            ]
        return pl


class Position(BaseModel):
    AveragePrice: float
    Quantity: int
    Symbol: str
    Timestamp: datetime


def df_from_bars(bars):
    bars_df = pd.DataFrame.from_records(bars)
    bars_df["TimeStamp"] = pd.to_datetime(bars_df["TimeStamp"])
    bars_df["TimeStamp"] = bars_df["TimeStamp"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    bars_df = bars_df.loc[:, ["TimeStamp", "Open", "High", "Low", "Close", "TotalVolume"]]
    bars_df["Open"] = bars_df["Open"].astype(float)
    bars_df["High"] = bars_df["High"].astype(float)
    bars_df["Low"] = bars_df["Low"].astype(float)
    bars_df["Close"] = bars_df["Close"].astype(float)
    bars_df["TotalVolume"] = bars_df["TotalVolume"].astype(int)
    bars_df.rename(columns={"TimeStamp": "datetime", "Open": "open", "High": "high", "Low": "low", "Close": "close", "TotalVolume": "volume"}, inplace=True)
    bars_df["date"] = bars_df["datetime"].dt.date
    return bars_df.sort_values("datetime")


class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        else:
            instance = cls._instances[cls]
            if hasattr(cls, '__allow_reinitialization') and cls.__allow_reinitialization:
                instance.__init__(*args, **kwargs)
        return instance


class TradestationAPI(metaclass=Singleton):
    def __init__(self, logger=None):
        self.api_key = os.getenv("TS_API_KEY")
        self.api_secret = os.getenv("TS_API_SECRET")
        self.base_url = "https://signin.tradestation.com"
        self.access_token = None
        self._access_token_semaphore = asyncio.Semaphore(1)
        self._access_token_last_refreshed = None
        self.refresh_token = os.getenv("TS_REFRESH_TOKEN")  # Get refresh token from environment
        self._account_id = os.getenv("TS_ACCOUNT_ID")
        is_sim = "SIM" in self._account_id
        self.api_url = f"https://{'sim-' if is_sim else ''}api.tradestation.com/v3"
        self._logger = logger or logging.getLogger(__name__)
        self._ignore_symbol_list = []

    @retry(TemporaryError, tries=3, delay=2, backoff=2)
    def _refresh_access_token(self, force=False):
        if not force and self._access_token_last_refreshed and datetime.now() - Timedelta(minutes=10) < self._access_token_last_refreshed:
            return

        token_url = f"{self.base_url}/oauth/token"
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'refresh_token',
            'client_id': self.api_key,
            'client_secret': self.api_secret,
            'refresh_token': self.refresh_token,
        }
        response = requests.post(token_url, headers=headers, data=data)
        try:
            response.raise_for_status()
        except HTTPError as err:
            logger.error(f"Error while refreshing access token: {err}")
            if response.status_code >= 500:
                raise TemporaryError(response.text)
            else:
                raise err

        response = response.json()
        self._access_token_last_refreshed = datetime.now()
        self.access_token = response['access_token']
        logger.info("Access token refreshed")

    @retry(TemporaryError, tries=3, delay=2, backoff=2)
    async def _request_endpoint(self, endpoint, params=None, headers=None, method="GET", data=None):
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        } | (headers or {})
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url=endpoint, headers=headers, params=params, json=data) as response:
                try:
                    response_json = await response.json()
                    if "Error" in response_json:
                        raise ClientResponseError(
                            response.request_info,
                            response.history,
                            status=response.status,
                            message=response_json["Error"],
                            headers=response.headers
                        )
                    return response_json
                except ClientResponseError as err:
                    logger.error(f"Error while requesting endpoint: {err}")
                    if err.status >= 500:
                        raise TemporaryError(await response.text())
                    elif err.status in (401, 403):
                        self._refresh_access_token(force=True)
                        return await self._request_endpoint(endpoint, params=params, headers=headers, method=method, data=data)
                    elif err.status == 429:
                        logger.warning("Rate limit exceeded. Waiting for 1 minute.")
                        await asyncio.sleep(60)
                        return await self._request_endpoint(endpoint, params=params, headers=headers, method=method, data=data)
                    else:
                        raise err

    @retry(TemporaryError, tries=3, delay=5, backoff=2)
    def _request_endpoint_sync(self, endpoint, params=None, headers=None, iterator=False, method="GET", data=None):
        headers = {
            'Authorization': f'Bearer {self.access_token}'
        } | (headers or {})
        response = requests.request(method, endpoint, headers=headers, data=json.dumps(data), params=params, stream=iterator)
        try:
            response.raise_for_status()
            if iterator:
                return response

            return response.json()
        except HTTPError as err:
            logger.error(f"Error while requesting endpoint: {err}")
            if response.status_code >= 500:
                raise TemporaryError(response.text)
            elif response.status_code == 401:
                self._refresh_access_token(force=True)
                return self._request_endpoint_sync(endpoint, params=params, headers=headers, iterator=iterator, method=method, data=data)
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded. Waiting for 1 minute.")
                time.sleep(60)
                return self._request_endpoint_sync(endpoint, params=params, headers=headers, iterator=iterator, method=method, data=data)
            else:
                raise err

    @refresh_token
    async def get_intraday_data(self, symbols, dates):
        async def _req_symbol(symbol, date):
            endpoint = f"{self.api_url}/marketdata/barcharts/{symbol}"
            try:
                date = min(date, datetime.now())
                bars = await self._request_endpoint(endpoint, params={
                    'interval': 5,
                    'unit': 'Minute',
                    'lastdate': date.strftime("%Y-%m-%d"),
                    'barsback': 78
                })
            except Exception as e:
                return pd.DataFrame()

            bars_df = df_from_bars(bars["Bars"])
            bars_df["symbol"] = symbol
            return bars_df

        tasks = [_req_symbol(symbol, date) for symbol, date in zip(symbols, dates)]
        return pd.concat(await asyncio.gather(*tasks))

    @refresh_token
    async def get_historical_intraday_data(self, symbols, start_date, end_date=None, interval=1):
        end_date = end_date or datetime.now()
        max_bars_back = 57600
        bars_in_a_day = (60 * 6.5) // interval
        if np.busday_count(start_date, end_date) * bars_in_a_day > max_bars_back:
            raise ValueError("Date range too large")

        async def _req_symbol(symbol):
            if symbol in self._ignore_symbol_list:
                return pd.DataFrame()

            endpoint = f"{self.api_url}/marketdata/barcharts/{symbol}"
            try:
                bars = await self._request_endpoint(endpoint, params={
                    'interval': interval,
                    'unit': 'Minute',
                    'lastdate': end_date,
                    'firstdate': start_date
                })
                logging.debug(f"Collected interval:{interval} bars for {symbol} from {start_date} to {end_date}")
            except ClientResponseError as err:
                logging.warning(repr(err))
                if err.status in (404, 400):
                    self._ignore_symbol_list.append(symbol)

                return pd.DataFrame()

            bars_df = df_from_bars(bars["Bars"])
            bars_df["symbol"] = symbol
            return bars_df

        tasks = [_req_symbol(symbol) for symbol in symbols]
        return pd.concat(await asyncio.gather(*tasks))

    @refresh_token
    async def get_current_day_intraday_bars(self, symbol: str):
        endpoint = f"{self.api_url}/marketdata/barcharts/{symbol}"
        try:
            bars = await self._request_endpoint(endpoint, params={
                'interval': 5,
                'unit': 'Minute',
                'firstdate': datetime.now(tz=pytz.timezone("US/Eastern")).replace(minute=30, hour=9).isoformat(),
            })
            return df_from_bars(bars["Bars"])
        except Exception as e:
            return pd.DataFrame()

    @refresh_token
    async def get_historical_daily_bars_single(self, symbol, days_back: int, last_date=datetime.now()):
        endpoint = f"{self.api_url}/marketdata/barcharts/{symbol}"
        try:
            bars = await self._request_endpoint(endpoint, params={
                'interval': 1,
                'unit': 'Daily',
                'barsback': days_back,
                'lastdate': last_date.strftime("%Y-%m-%d")
            })
            df = df_from_bars(bars["Bars"])
        except Exception as e:
            df = pd.DataFrame()
        return df

    @refresh_token
    async def get_historical_daily_bars(
            self,
            symbols,
            days_back: int,
            df_queue: asyncio.Queue,
            last_date=datetime.now()
    ):
        async def _req_symbol(symbol_queue, df_queue):
            while True:
                symbol = await symbol_queue.get()
                df = await self.get_historical_daily_bars_single(symbol, days_back, last_date)
                if not df.empty and df.iloc[-1].datetime.date() < (last_date - timedelta(days=5)).date():
                    df = pd.DataFrame()
                await df_queue.put((symbol, df))
                symbol_queue.task_done()

        symbol_queue = asyncio.Queue()
        for symbol in symbols:
            symbol_queue.put_nowait(symbol)

        workers = []
        for _ in range(5):
            workers.append(asyncio.create_task(_req_symbol(symbol_queue, df_queue)))

        await symbol_queue.join()
        for worker in workers:
            worker.cancel()
        await asyncio.gather(*workers, return_exceptions=True)

    @refresh_token
    async def get_bars(
        self,
        symbol: str,
        interval: int,
        unit: str,
        barsback: Optional[int] = None,
        firstdate: Optional[str] = None,
        lastdate: Optional[str] = None,
        extended_hours: bool = False
    ):
        endpoint = f"{self.api_url}/marketdata/barcharts/{symbol}"
        params = {
            'interval': interval,
            'unit': unit
        }
        if (barsback and firstdate) or (not barsback and not firstdate):
            raise ValueError("Either barsback or firstdate can be provided, not both")
        if barsback:
            params['barsback'] = barsback
        if firstdate:
            params['firstdate'] = firstdate
        if lastdate:
            params['lastdate'] = lastdate
        if extended_hours:
            params['sessiontemplate'] = 'USEQPreAndPost'

        bars = await self._request_endpoint(endpoint, params=params)
        return df_from_bars(bars["Bars"])


    @refresh_token
    def stream_bars(self, symbol: str) -> Iterator[pd.DataFrame]:
        url = f"https://api.tradestation.com/v3/marketdata/stream/barcharts/{symbol}"
        params = {
            "interval": 5,
            "unit": "Minute"
        }

        response = self._request_endpoint_sync(url, params=params, iterator=True)
        for line in response.iter_lines(decode_unicode=True):
            if line:
                ohlc = json.loads(line)
                if "High" not in ohlc:
                    self._logger.debug(ohlc)
                    if "Error" in ohlc:
                        logger.error(ohlc["Error"])
                        self._logger.debug("Reconnecting...")
                        return self.stream_bars(symbol)
                    else:
                        continue
                df = df_from_bars([ohlc])
                yield df.loc[:, ["datetime", "open", "high", "low", "close", "volume"]]

    @refresh_token
    def stream_quotes(self, symbol: str):
        url = f"https://api.tradestation.com/v3/marketdata/stream/quotes/{symbol}"

        response = self._request_endpoint_sync(url, iterator=True)

        for line in response.iter_lines(decode_unicode=True):
            if line:
                quote = json.loads(line)
                if "Heartbeat" in quote:
                    continue
                elif "Error" in quote:
                    logger.error(quote["Error"])
                    continue
                yield Quote(**quote)

    @refresh_token
    async def open_position(self, symbol: str, size: int, tp: float=0, sl: float=0, order_type="Market", price=None) -> list[dict]:
        symbol = symbol.upper()
        endpoint = f"{self.api_url}/orderexecution/orders"
        headers = {
            'Content-Type': 'application/json'
        }
        oso = []
        if tp > 0:
            oso.append(CreateOrder(
                Symbol=symbol,
                Quantity=size,
                TradeAction="SELL",
                OrderType="Limit",
                TimeInForce={"Duration": "DAY" if is_market_open() else "DYP"},
                LimitPrice=round(tp, 2)
            ))
        if sl > 0:
            oso.append(CreateOrder(
                Symbol=symbol,
                Quantity=size,
                TradeAction="SELL",
                OrderType="StopMarket",
                TimeInForce={"Duration": "DAY" if is_market_open() else "DYP"},
                StopPrice=round(sl, 2)
            ))
        create_order_body = CreateOrder(
            Symbol=symbol,
            Quantity=size,
            OrderType=order_type,
            TimeInForce={"Duration": "DAY" if is_market_open() else "DYP"},
            TradeAction="BUY",
            LimitPrice=price if order_type == "Limit" else None,
            StopPrice=price if order_type == "StopMarket" else None,
            OSOs=oso if oso else None
        ).to_payload()
        response = await self._request_endpoint(endpoint, method="POST", headers=headers, data=create_order_body)
        orders = response["Orders"]
        return orders

    @refresh_token
    async def close_position(self, symbol: str, size: int, order_type="Market", limit_price=None):
        endpoint = f"{self.api_url}/orderexecution/orders"
        headers = {
            'Content-Type': 'application/json'
        }
        order = CreateOrder(
            Symbol=symbol,
            Quantity=int(size),
            OrderType=order_type,
            TimeInForce={"Duration": "Day"},
            TradeAction="SELL",
        )
        if order_type == "Limit":
            order.LimitPrice = limit_price
        payload = order.to_payload()
        await self._request_endpoint(endpoint, headers=headers, method="POST", data=payload)


    @refresh_token
    async def get_positions(self) -> list[dict]:
        endpoint = f"{self.api_url}/brokerage/accounts/{self._account_id}/positions"
        response = await self._request_endpoint(endpoint)
        return response["Positions"]


    @refresh_token
    async def get_balances(self):
        endpoint = f"{self.api_url}/brokerage/accounts/{self._account_id}/balances"
        response = await self._request_endpoint(endpoint)
        return response["Balances"]

tradestation = TradestationAPI()
