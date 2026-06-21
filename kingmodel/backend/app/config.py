from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_secret: str = "development-only-change-me"
    admin_username: str = "king"
    admin_password: str = "kingmodel-dev"
    database_path: str = "./data/kingmodel.db"
    tdx_mcp_url: str = ""
    tdx_mcp_token: str = ""
    tdx_mcp_tool: str = "tdx_screener"
    collect_interval_seconds: int = 60
    session_hours: int = 12

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
