"""アプリケーション全体の設定値読み込みロジック."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable

from pydantic import AliasChoices, Field, PostgresDsn, SecretStr, field_validator
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    environment: str = Field(default="TEST", validation_alias=AliasChoices("ENVIRONMENT", "environment"))

    database_url_test: PostgresDsn = Field(validation_alias=AliasChoices("DATABASE_URL_TEST", "DATABASE_URL"))
    database_url_stg: PostgresDsn | None = Field(default=None, validation_alias=AliasChoices("DATABASE_URL_STG", "DATABASE_URL_STAGE"))
    database_url_prod: PostgresDsn | None = Field(default=None, validation_alias=AliasChoices("DATABASE_URL_PROD", "DATABASE_URL_PRODUCTION"))

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

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment(cls, value: Any) -> str:
        if value is None:
            return "TEST"
        if isinstance(value, str):
            normalized = value.strip().upper()
            return normalized or "TEST"
        raise ValueError("ENVIRONMENTは文字列で指定してください。")

    def _database_url_for(self, environment: str | None = None) -> PostgresDsn:
        env = (environment or self.environment).upper()
        mapping: dict[str, PostgresDsn | None] = {
            "TEST": self.database_url_test,
            "STG": self.database_url_stg,
            "PROD": self.database_url_prod,
        }
        dsn = mapping.get(env)
        if dsn is None:
            raise ValueError(f"ENVIRONMENTに対応する接続先が未設定です: {env}")
        return dsn

    @staticmethod
    def _to_async_dsn(dsn: str) -> str:
        if dsn.startswith("postgresql+asyncpg"):
            return dsn
        if dsn.startswith("postgresql://"):
            return "postgresql+asyncpg://" + dsn[len("postgresql://") :]
        return dsn

    @property
    def database_url(self) -> str:
        """現在のENVIRONMENTに対応する同期接続文字列."""
        return str(self._database_url_for())

    @property
    def async_database_url(self) -> str:
        """SQLAlchemy AsyncEngine向けの接続文字列を返す."""
        return self._to_async_dsn(self.database_url)

    def async_database_url_for(self, environment: str) -> str:
        """指定ENVIRONMENTのAsyncEngine向け接続文字列."""
        return self._to_async_dsn(str(self._database_url_for(environment)))

    @property
    def async_test_database_url(self) -> str | None:
        """テスト用DBのAsyncEngine向け接続文字列."""
        try:
            return self.async_database_url_for("TEST")
        except ValueError:
            return None

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
