from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "pos-system"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    TIMEZONE: str = "America/Bogota"

    SECRET_KEY: str = "CHANGE_ME_64_CHARACTERS_RANDOM"

    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "pos_db"
    POSTGRES_USER: str = "pos_user"
    POSTGRES_PASSWORD: str = "dev_password_123"

    DATABASE_URL: str = ""

    @property
    def resolved_database_url(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            if "sslmode=" in url:
                url = url.split("?sslmode=")[0] if "?sslmode=" in url else url.replace("&sslmode=require", "").replace("&sslmode=prefer", "")
            return url
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def database_ssl_required(self) -> bool:
        return "sslmode=require" in self.DATABASE_URL

    @property
    def resolved_database_url_sync(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("+asyncpg", "")
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "CHANGE_ME_64_CHARACTERS_RANDOM"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # --- 2FA / dispositivos confiables ---
    AUTH_2FA_ENABLED: bool = True
    AUTH_2FA_DEV_MODE: bool = False
    AUTH_2FA_CODE_MINUTES: int = 10
    DEVICE_TRUST_DAYS: int = 30
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@pos.local"
    SMTP_STARTTLS: bool = True
    SMTP_SSL: bool = False

    VAPID_PRIVATE_KEY_PATH: str = ""
    VAPID_PUBLIC_KEY_PATH: str = ""
    VAPID_CLAIM_EMAIL: str = "mailto:admin@tudominio.com"
    _vapid_private_key: str | None = None
    _vapid_public_key: str | None = None

    PAC_PROVIDER: str = "carvajal"
    PAC_CREDENTIALS_PATH: str = ""
    DIAN_ENVIRONMENT: Literal["homologacion", "produccion"] = "homologacion"
    DIAN_NIT: str = ""
    DIAN_PIN: str = ""

    IMPRESORA_TIPO: Literal["usb", "red"] = "usb"
    IMPRESORA_USB_VID: str = "0x0483"
    IMPRESORA_USB_PID: str = "0x5740"
    IMPRESORA_RED_HOST: str = ""
    IMPRESORA_RED_PORT: int = 9100

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @property
    def vapid_private_key(self) -> str:
        if self._vapid_private_key is None:
            if self.VAPID_PRIVATE_KEY_PATH and Path(self.VAPID_PRIVATE_KEY_PATH).exists():
                self._vapid_private_key = Path(self.VAPID_PRIVATE_KEY_PATH).read_text().strip()
            else:
                self._vapid_private_key = ""
        return self._vapid_private_key

    @property
    def vapid_public_key(self) -> str:
        if self._vapid_public_key is None:
            if self.VAPID_PUBLIC_KEY_PATH and Path(self.VAPID_PUBLIC_KEY_PATH).exists():
                self._vapid_public_key = Path(self.VAPID_PUBLIC_KEY_PATH).read_text().strip()
            else:
                self._vapid_public_key = ""
        return self._vapid_public_key

    @property
    def pac_credentials(self) -> dict:
        if self.PAC_CREDENTIALS_PATH and Path(self.PAC_CREDENTIALS_PATH).exists():
            return json.loads(Path(self.PAC_CREDENTIALS_PATH).read_text())
        return {}

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
