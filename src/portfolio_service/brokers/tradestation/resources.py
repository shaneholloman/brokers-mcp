import json

from mcp import Resource
from pydantic import AnyUrl
from .api import tradestation
from ..common import BrokerResources

tradestation_host = "tradestation"

def endpoint_uri(protocol: str, endpoint: str) -> AnyUrl:
    return AnyUrl(f"{protocol}://{tradestation_host}/{endpoint}")


async def handle_resource_call(uri: AnyUrl):
    if uri == endpoint_uri(protocol="brokerage", endpoint="balances"):
        return json.dumps(await tradestation.get_balances())
    elif uri == endpoint_uri(protocol="brokerage", endpoint="positions"):
        return json.dumps(await tradestation.get_positions())
    else:
        raise ValueError(f"Unknown resource URI: {uri}")

resources = BrokerResources(
    host = tradestation_host,
    resources=[
        Resource(
            uri=endpoint_uri(protocol="brokerage", endpoint="balances"),
            name="get_balances",
            description="Get account balances",
            mimeType="application/json",
        ),
        Resource(
            uri=endpoint_uri(protocol="brokerage", endpoint="positions"),
            name="get_positions",
            description="Get current account positions",
            mimeType="application/json",
        )
    ],
    handler=handle_resource_call
)
