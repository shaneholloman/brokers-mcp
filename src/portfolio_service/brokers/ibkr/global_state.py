import asyncio

from ib_insync import Contract, Stock

from .client import ib

orders = {}

class ContractCache(dict):
    def __init__(self, ib_client):
        super().__init__()
        self.contracts = {}
        self.ib_client = ib_client

    async def get(self, contract: Contract) -> Contract | None:
        if contract.conId in self.contracts:
            return self.contracts[contract.conId]
        else:
            contract = await self.ib_client.qualifyContractsAsync(contract) # invalid contract (could happen if strike doesn't exist)
            if not contract:
                return None

            contract = contract[0]
            self.contracts[contract.conId] = contract
            return self.contracts[contract.conId]

cache = ContractCache(ib)

async def qualify_contracts(*contracts: Contract) -> list[Contract]:
    return await asyncio.gather(*[cache.get(c) for c in contracts])

async def get_contract(symbol: str, contract_type: str, currency: str = "USD") -> Contract:
    if contract_type == "stock":
        contract = Stock(symbol, "SMART", currency)
    elif contract_type == "index":
        raise NotImplementedError("Index is not yet supported")
    else:
        raise ValueError(f"Unknown symbol type: {contract_type}")
    contracts = await qualify_contracts(contract)
    return contracts[0]

news_providers: list[str] = []