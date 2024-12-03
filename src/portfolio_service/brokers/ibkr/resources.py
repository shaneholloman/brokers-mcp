from datetime import datetime, timedelta

from ib_insync import Stock
from mcp import Resource
from pydantic import AnyUrl

from .client import ib
from ..common import BrokerResources, list_items

ib_host = "ibkr"

def endpoint_uri(protocol: str, endpoint: str) -> AnyUrl:
    return AnyUrl(f"{protocol}://{ib_host}/{endpoint}")


resource_list = [
    Resource(
        uri=endpoint_uri(protocol="brokerage", endpoint="portfolio"),
        name="portfolio",
        description="Get account portfolio holdings, including stocks, options, and futures",
        mimeType="plain/text",
    ),
    Resource(
        uri=endpoint_uri(protocol="brokerage", endpoint="account_summary"),
        name="account_summary",
        description="Get account summary",
        mimeType="plain/text",
    ),
    Resource(
        uri=endpoint_uri(protocol="brokerage", endpoint="all_orders"),
        name="all_orders",
        description="Get all orders in the account from the current session",
        mimeType="plain/text",
    ),
    Resource(
        uri=endpoint_uri(protocol="brokerage", endpoint="open_orders"),
        name="open_orders",
        description="Get all open orders in the account",
        mimeType="plain/text",
    ),
]

async def handle_resource_call(uri: AnyUrl) -> str:
    if uri.path == "/portfolio":
        portfolio = ib.portfolio() # the return value
        return list_items(portfolio)
    elif uri.path == "/account_summary":
        tags =  ('AccountType,NetLiquidation,TotalCashValue,SettledCash,'
                'AccruedCash,BuyingPower,EquityWithLoanValue,'
                'PreviousDayEquityWithLoanValue,GrossPositionValue').split(',')
        account_values = ib.accountSummary()
        filtered = {value.tag: value.value for value in account_values if value.tag in tags}
        return list_items(filtered)
    elif uri.path == "/all_orders":
        return "#### ALL SESSION TRADES ####\n"+ list_items(ib.trades())
    elif uri.path == "/open_orders":
        return "#### SESSION OPEN TRADES ####\n"+list_items(ib.openTrades())
    else:
        raise ValueError(f"Unknown resource path: {uri.path}")

resources = BrokerResources(
    host=ib_host,
    resources=resource_list,
    handler=handle_resource_call
)

