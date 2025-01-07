from ib_insync import IB

ib: IB | None = None

def get_ib() -> IB:
    if ib is None:
        raise RuntimeError("IB client not initialized")
    return ib

def set_ib(client: IB):
    global ib
    ib = client 