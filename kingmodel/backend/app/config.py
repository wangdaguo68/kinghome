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
    tushare_token: str = ""
    tushare_api_url: str = "https://api.tushare.pro"
    collect_interval_seconds: int = 86400
    tdx_daily_call_limit: int = 5
    tdx_close_enrichment_enabled: bool = False
    close_collection_hour: int = 15
    close_collection_minute: int = 10
    session_hours: int = 12

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
