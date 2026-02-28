from functools import lru_cache
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Ecom API"
    APP_ENV: str = "dev"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    ENABLE_DOCS: bool = True

    DATABASE_URL: str = "sqlite:///./ecom.db"
    SQL_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE_SECONDS: int = 1800

    APP_CURRENCY: str = "INR"
    USD_TO_INR_RATE: float = 83.0
    FREE_DELIVERY_THRESHOLD: float = 1000.0
    DELIVERY_CHARGE: float = 100.0

    CORS_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://0.0.0.0:5173",
    ]
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = ["*"]
    ENABLE_HTTPS_REDIRECT: bool = False
    ENABLE_GZIP: bool = True
    GZIP_MINIMUM_SIZE: int = 1000

    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD: str = "Admin@1234"
    SEED_DEMO_USERS: bool = True
    DEMO_ADMIN_USERNAME: str = "ecomadmin"
    DEMO_ADMIN_EMAIL: str = "ecomadmin@example.com"
    DEMO_ADMIN_PASSWORD: str = "ecom@123admin"
    DEMO_VENDOR_USERNAME: str = "ecomvendor"
    DEMO_VENDOR_EMAIL: str = "ecomvendor@example.com"
    DEMO_VENDOR_PASSWORD: str = "ecom@123vendor"

    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None
    PAYTM_MERCHANT_ID: str | None = None
    PAYTM_MERCHANT_KEY: str | None = None

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [host.strip() for host in value.split(",") if host.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.APP_ENV.lower() not in {"prod", "production"}:
            return self

        if self.DEBUG:
            raise ValueError("DEBUG must be false in production")
        if self.JWT_SECRET_KEY == "change-this-in-production":
            raise ValueError("JWT_SECRET_KEY must be changed in production")
        if self.DEFAULT_ADMIN_PASSWORD == "Admin@1234":
            raise ValueError("DEFAULT_ADMIN_PASSWORD must be changed in production")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
