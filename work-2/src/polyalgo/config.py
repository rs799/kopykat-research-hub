from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/polyalgo.sqlite"

    polymarket_gamma_base: str = "https://gamma-api.polymarket.com"
    polymarket_clob_base: str = "https://clob.polymarket.com"
    polymarket_data_base: str = "https://data-api.polymarket.com"

    trading_mode: str = "paper"

    max_risk_per_trade: float = 0.005
    max_market_exposure: float = 0.03
    max_daily_loss: float = 0.02
    min_wallet_score: float = 75.0
    min_net_edge: float = 0.04
    max_spread: float = 0.03

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

