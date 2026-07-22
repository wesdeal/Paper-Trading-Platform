from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str
    test_database_url: str | None = None  # test-only; not required to boot api/worker
    redis_url: str
    secret_key: str
    finn_api_key: str

settings = Settings()