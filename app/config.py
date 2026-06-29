"""Application configuration loaded from environment variables.

Uses pydantic-settings so every value is validated and typed.
"""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Strongly-typed settings, populated from the environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")

    postgres_host: str = Field(alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(alias="POSTGRES_DB")

    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

    deposit_commission_percent: Decimal = Field(
        default=Decimal("0"), alias="DEPOSIT_COMMISSION_PERCENT"
    )
    withdraw_commission_percent: Decimal = Field(
        default=Decimal("0"), alias="WITHDRAW_COMMISSION_PERCENT"
    )
    commission_tg_id: str = Field(default="", alias="COMMISSION_TG_ID")

    crypto_pay_token: str = Field(default="", alias="CRYPTO_PAY_TOKEN")
    crypto_pay_testnet: bool = Field(default=True, alias="CRYPTO_PAY_TESTNET")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def database_url(self) -> URL:
        """Async SQLAlchemy connection URL (asyncpg driver).

        Built via ``URL.create`` so passwords with special characters
        (``%``, ``)``, ``@`` …) are stored safely without manual escaping
        or configparser interpolation issues.
        """
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @computed_field
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def admin_id_list(self) -> list[int]:
        """Parse the comma-separated ADMIN_IDS string into a list of ints."""
        return [int(x) for x in self.admin_ids.split(",") if x.strip()]

    @property
    def commission_recipient_id(self) -> int | None:
        """Telegram id that should receive auto-forwarded commissions.

        Uses COMMISSION_TG_ID when set, otherwise the first ADMIN_IDS entry;
        ``None`` when neither is configured (commissions are then not forwarded).
        """
        if self.commission_tg_id.strip():
            return int(self.commission_tg_id.strip())
        admins = self.admin_id_list
        return admins[0] if admins else None


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — read the environment only once."""
    return Settings()


settings = get_settings()
