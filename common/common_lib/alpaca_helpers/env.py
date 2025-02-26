from pydantic_settings import BaseSettings, SettingsConfigDict


class AlpacaSettings(BaseSettings):
    api_key: str
    api_secret: str
    simulation: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALPACA_", extra="ignore")
