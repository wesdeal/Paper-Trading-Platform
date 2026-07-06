from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    test_database_url: str = ""  # only needed when running pytest
    redis_url: str = ""          # unused for now; kept for docker-compose compatibility
    secret_key: str

    # comma-separated list of allowed frontend origins
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # market data + background job tuning
    price_cache_ttl_seconds: int = 15
    limit_order_poll_seconds: int = 20
    snapshot_interval_seconds: int = 300
    ws_update_interval_seconds: int = 15

    # lets tests / one-off scripts import the app without spawning loops
    enable_background_tasks: bool = True

settings = Settings()