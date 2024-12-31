import os

import pytz
from ib_insync import IB

ib = IB()
ib.TimezoneTWS = pytz.timezone("US/Eastern")
ib.connect('127.0.0.1', 7496, clientId=3, account=os.getenv("IBKR_ACCOUNT"), timeout=30)