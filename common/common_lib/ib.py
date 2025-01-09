import os
from ib_insync import IB
import pytz
import asyncio
from ib_insync import Contract, Stock

ib: IB | None = None

def get_ib() -> IB:
    if ib is None:
        raise RuntimeError("IB client not initialized")
    return ib

def set_ib(client: IB):
    global ib
    ib = client

def connect_ib():
    client_id = os.getenv("IBKR_CLIENT_ID", 1)
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    port = int(os.getenv("IBKR_PORT", "7496"))
    account = os.getenv("IBKR_ACCOUNT")
    ib = IB()
    ib.TimezoneTWS = pytz.timezone("US/Eastern")
    ib.connect(host, port, clientId=client_id, account=account, timeout=30)
    set_ib(ib)
    return ib

class ContractCache(dict):
    def __init__(self):
        super().__init__()
        self.contracts = {}

    async def get(self, contract: Contract) -> Contract | None:
        ib = get_ib()
        if contract.conId in self.contracts:
            return self.contracts[contract.conId]
        else:
            contract = await ib.qualifyContractsAsync(contract) # invalid contract (could happen if strike doesn't exist)
            if not contract:
                return None

            contract = contract[0]
            self.contracts[contract.conId] = contract
            return self.contracts[contract.conId]

cache = ContractCache()

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
