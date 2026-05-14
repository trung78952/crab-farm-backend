from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Crab Farm Backend"
    app_env: str = "local"
    debug: bool = True
    app_timezone: str = "Asia/Ho_Chi_Minh"
    simulation_mode: bool = True

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
    mqtt_simulate_publish: bool = False

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]
    storage_dir: Path = Path("storage")
    public_storage_url: str = "/storage"

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    admin_username: str = "admin"
    admin_password: str = "admin123"
    admin_email: str = "admin@example.com"

    molting_recheck_minutes: int = 10
    uncertain_recheck_minutes: int = 3
    soft_shell_verify_seconds: int = 60
    soft_shell_confidence_threshold: float = 0.85

    motion_timeout_seconds: int = 60
    camera_timeout_seconds: int = 30
    ai_timeout_seconds: int = 30
    motion_settle_ms: int = 800

    ai_enabled: bool = True
    ai_mock_mode: bool = False
    ai_model_path: str = "storage/models/crab_yolov8_v1.pt"
    ai_model_version: str = "crab_yolov8_v1"
    ai_confidence_threshold: float = 0.5
    ai_image_size: int = 640

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
