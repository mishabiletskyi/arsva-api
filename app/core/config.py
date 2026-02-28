from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Automated Rent Status Voice Assistant API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    backend_cors_origins: List[str] = ["http://localhost:5173"]

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "arsva_db"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    azure_blob_connection_string: str = ""
    azure_blob_container_uploads: str = "uploads"
    azure_blob_container_exports: str = "exports"
    azure_blob_container_recordings: str = "call-recordings"

    jwt_secret_key: str = "change_me_super_secret_key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def sqlalchemy_database_uri(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()