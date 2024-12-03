import asyncio

from ib_insync import Contract

from .client import ib

orders = {}

class ContractCache(dict):
    def __init__(self, ib_client):
        super().__init__()
        self.contracts = {}
        self.ib_client = ib_client

    async def get(self, contract: Contract) -> Contract:
        if contract.conId in self.contracts:
            return self.contracts[contract.conId]
        else:
            self.contracts[contract.conId] = (await self.ib_client.qualifyContractsAsync(contract))[0]
            return self.contracts[contract.conId]

cache = ContractCache(ib)

async def qualify_contracts(*contracts: Contract) -> list[Contract]:
    return await asyncio.gather(*[cache.get(c) for c in contracts])

news_providers: list[str] = []