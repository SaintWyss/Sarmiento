from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SARMIENTO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "sqlite:///./sarmiento.db"
    owner_username: str = "owner"
    owner_password: str = "change-me-now"
    session_secret: str = "development-secret-change-me-please-32-bytes"
    token_pepper: str | None = None
    session_ttl_minutes: int = Field(default=720, ge=15, le=10080)
    cookie_secure: bool = False
    csrf_enabled: bool = True
    allowed_origins: str = "http://localhost,http://127.0.0.1"
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    presence_threshold_seconds: int = Field(default=90, ge=30, le=3600)
    enrollment_ttl_minutes: int = Field(default=15, ge=1, le=1440)
    public_base_url: str = "http://localhost"
    rustdesk_server: str = "localhost"
    rustdesk_key: str = ""
    rustdesk_key_file: str = ""
    rate_limit_per_minute: int = Field(default=120, ge=10, le=10000)
    login_rate_limit_per_minute: int = Field(default=10, ge=1, le=100)
    max_rate_limit_buckets: int = Field(default=10000, ge=100, le=1000000)
    max_request_body_bytes: int = Field(default=65536, ge=16384, le=1048576)
    login_lockout_attempts: int = Field(default=5, ge=3, le=20)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440)
    static_dir: str = "../front"
    agent_dir: str = "../agent"
    viewer_dir: str = "../viewer"

    @field_validator("session_secret")
    @classmethod
    def validate_session_secret(cls, value: str) -> str:
        if len(value.encode("utf-8")) < 32:
            raise ValueError("SARMIENTO_SESSION_SECRET must be at least 32 bytes")
        return value

    @property
    def origins(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def hosts(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts.split(",") if item.strip()]

    @property
    def effective_token_pepper(self) -> str:
        return self.token_pepper or self.session_secret

    @property
    def session_cookie_name(self) -> str:
        return "__Host-sarmiento_session" if self.cookie_secure else "sarmiento_session"

    @property
    def csrf_cookie_name(self) -> str:
        return "__Host-sarmiento_csrf" if self.cookie_secure else "sarmiento_csrf"

    @property
    def resolved_rustdesk_key(self) -> str:
        if self.rustdesk_key.strip():
            return self.rustdesk_key.strip()
        if self.rustdesk_key_file:
            try:
                return __import__("pathlib").Path(self.rustdesk_key_file).read_text().strip()
            except OSError:
                return ""
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
