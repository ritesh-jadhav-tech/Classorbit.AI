from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ClassOrbit Backend"
    api_prefix: str = "/api"
    environment: str = "development"

    database_url: str = "sqlite:///./classorbit.db"
    secret_key: str = Field(default="change-this-secret-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    uploads_dir: str = "uploads"
    max_upload_mb: int = 25
    tesseract_cmd: str | None = None
    create_missing_classrooms_from_import: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def uploads_path(self) -> Path:
        path = Path(self.uploads_dir)
        if not path.is_absolute():
            path = self.project_root / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
