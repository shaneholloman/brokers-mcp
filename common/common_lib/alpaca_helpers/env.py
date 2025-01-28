from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import validator
from datetime import datetime

from pytz import timezone

class AlpacaSettings(BaseSettings):
    api_key: str
    api_secret: str
    simulation: bool = False
    asof: Optional[datetime] = None # for simulation, the bars_back parameter end date is set to this value. format as YYYY-MM-DDTHH:MM:SSZ

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALPACA_", extra="ignore")

    @validator("asof", pre=True, always=True)
    def parse_asof(cls, value):
        if value:
            return datetime.fromisoformat(value).astimezone(timezone("US/Eastern"))
        return None