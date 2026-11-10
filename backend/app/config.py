from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MarketGuard"
    app_env: str = "development"
    debug: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "marketguard_db"
    postgres_user: str = "postgres"
    postgres_password: str = "CHANGE_ME"

    data_seed: int = 20261022
    data_scale: str = "starter"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
