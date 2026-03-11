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
    vapi_private_api_key: str = ""
    vapi_api_base_url: str = "https://api.vapi.ai"
    vapi_default_assistant_id: str = ""
    vapi_phone_number_id: str = ""
    vapi_webhook_secret: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_phone_number: str = ""
    twilio_api_base_url: str = "https://api.twilio.com/2010-04-01"

    sms_after_call_enabled: bool = True
    sms_send_outcomes: List[str] = ["paying_soon", "need_assistance", "needs_assistance"]
    payment_portal_url: str = ""

    current_script_version: str = "rent-status-v1"
    # Deprecated: dynamic call policy now comes from DB (call_policies table).
    call_window_start_hour: int = 8
    call_window_end_hour: int = 21
    max_calls_7_days: int = 2
    max_calls_30_days: int = 4
    min_hours_between_calls: float = 72
    pilot_min_days_late: int = 3
    pilot_max_days_late: int = 10
    pilot_max_batch_size: int = 50

    jwt_secret_key: str = "change_me_super_secret_key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 180

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

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no"}:
                return False
            if normalized in {"dev", "development", "true", "1", "yes"}:
                return True
        return value

    @field_validator("sms_send_outcomes", mode="before")
    @classmethod
    def parse_sms_send_outcomes(cls, value):
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
