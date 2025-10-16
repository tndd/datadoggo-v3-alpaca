"""アプリケーション全体の設定値読み込みロジック."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable

from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_comma_separated(value: str | Iterable[str] | None) -> list[str]:
    """カンマ区切り文字列を安全にリストへ変換するヘルパー."""
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        return [chunk.strip() for chunk in value.split(",") if chunk.strip()]
    return [item.strip() for item in value if item]


class Settings(BaseSettings):
    """環境変数から動的に読み込まれる設定値."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: PostgresDsn
    test_database_url: PostgresDsn | None = None

    alpaca_api_key: SecretStr | None = None
    alpaca_secret_key: SecretStr | None = None
    alpaca_data_base_url: str = Field("https://data.alpaca.markets")

    default_stock_symbols: list[str] = Field(default_factory=list)
    default_crypto_symbols: list[str] = Field(default_factory=list)
    default_option_symbols: list[str] = Field(default_factory=list)
    default_news_symbols: list[str] = Field(default_factory=list)

    @field_validator(
        "default_stock_symbols",
        "default_crypto_symbols",
        "default_option_symbols",
        "default_news_symbols",
        mode="before",
    )
    @classmethod
    def _split_values(cls, value: Any) -> list[str]:
        return _split_comma_separated(value)

    @property
    def async_database_url(self) -> str:
        """SQLAlchemy AsyncEngine向けの接続文字列を返す."""
        dsn = str(self.database_url)
        if dsn.startswith("postgresql+asyncpg"):
            return dsn
        if dsn.startswith("postgresql://"):
            return "postgresql+asyncpg://" + dsn[len("postgresql://") :]
        return dsn

    @property
    def async_test_database_url(self) -> str | None:
        """テスト用DBのAsyncEngine向け接続文字列."""
        if self.test_database_url is None:
            return None
        dsn = str(self.test_database_url)
        if dsn.startswith("postgresql+asyncpg"):
            return dsn
        if dsn.startswith("postgresql://"):
            return "postgresql+asyncpg://" + dsn[len("postgresql://") :]
        return dsn

    @property
    def alpaca_credentials(self) -> tuple[str | None, str | None]:
        """Alpaca API向け認証情報をタプルで返却."""
        api_key = self.alpaca_api_key.get_secret_value() if self.alpaca_api_key else None
        secret_key = self.alpaca_secret_key.get_secret_value() if self.alpaca_secret_key else None
        return api_key, secret_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """設定値をシングルトンとして扱う."""
    return Settings()  # type: ignore[call-arg]
