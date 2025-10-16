"""アプリケーション全体の設定を管理するモジュール."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable

from pydantic import AliasChoices, Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_comma_separated(value: str | Iterable[str] | None) -> list[str]:
    """カンマ区切り文字列をリスト化する."""
    if value is None:
        return []
    if isinstance(value, str):
        if not value.strip():
            return []
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


class Settings(BaseSettings):
    """環境変数から読み込む設定値."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # ENVIRONMENTを指定しない場合はTEST扱い
    environment: str | None = Field(default=None, validation_alias=AliasChoices("ENVIRONMENT", "environment"))

    # 接続情報(DATABASE_URL_TESTが必須。DATABASE_URLでの指定にも対応)
    database_url_test: PostgresDsn | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL_TEST", "DATABASE_URL"),
    )
    database_url_stg: PostgresDsn | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL_STG", "DATABASE_URL_STAGE"),
    )
    database_url_prod: PostgresDsn | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL_PROD", "DATABASE_URL_PRODUCTION"),
    )

    alpaca_api_key: SecretStr | None = None
    alpaca_secret_key: SecretStr | None = None
    alpaca_data_base_url: str = Field(default="https://data.alpaca.markets")

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
    def effective_environment(self) -> str:
        """ENVIRONMENT未指定時はTESTを返す."""
        if self.environment is None:
            return "TEST"
        normalized = self.environment.strip().upper()
        return normalized or "TEST"

    def _database_url_for(self, environment: str | None = None) -> PostgresDsn:
        env = (environment or self.effective_environment).upper()
        mapping: dict[str, PostgresDsn | None] = {
            "TEST": self.database_url_test,
            "STG": self.database_url_stg,
            "PROD": self.database_url_prod,
        }
        dsn = mapping.get(env)
        if dsn is None:
            raise ValueError(f"ENVIRONMENTに対応するDATABASE_URLが未設定です: {env}")
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
        """同期接続用のDSN (ENVIRONMENTに応じて切り替え)."""
        return str(self._database_url_for())

    @property
    def async_database_url(self) -> str:
        """AsyncEngine向けDSN."""
        return self._to_async_dsn(self.database_url)

    def async_database_url_for(self, environment: str) -> str:
        return self._to_async_dsn(str(self._database_url_for(environment)))

    @property
    def async_test_database_url(self) -> str:
        if self.database_url_test is None:
            raise ValueError("DATABASE_URL_TESTが設定されていません")
        return self._to_async_dsn(str(self.database_url_test))

    @property
    def alpaca_credentials(self) -> tuple[str | None, str | None]:
        api_key = self.alpaca_api_key.get_secret_value() if self.alpaca_api_key else None
        secret_key = self.alpaca_secret_key.get_secret_value() if self.alpaca_secret_key else None
        return api_key, secret_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """設定インスタンスをシングルトンとして取得する."""
    return Settings()
