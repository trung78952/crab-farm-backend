from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Crab Farm Backend"
    app_env: str = "local"
    debug: bool = True

    database_url: str = Field(
        default="postgresql+asyncpg://crab:crab@postgres:5432/crab_farm",
        description="Async SQLAlchemy database URL.",
    )

    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_client_id: str = "crab-farm-backend"
    mqtt_keepalive: int = 60

    cors_origins: list[str] = ["http://localhost:5173"]
    storage_dir: Path = Path("storage")
    public_storage_url: str = "/storage"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
