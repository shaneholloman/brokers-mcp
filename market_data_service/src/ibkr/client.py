from contextvars import ContextVar

from ib_insync import IB

# Global IB client instance that can be accessed throughout the application
ib = None

def get_ib():
    global ib
    if ib is None:
        raise ValueError("IBKR client not initialized")
    return ib

def set_ib(new_ib):
    global ib
    ib = new_ib
