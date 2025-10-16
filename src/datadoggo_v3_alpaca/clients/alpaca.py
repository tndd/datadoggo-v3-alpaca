"""Alpaca SDKクライアントの初期化を担うモジュール."""

from __future__ import annotations

from typing import Optional

from alpaca.data import NewsClient
from alpaca.data.historical import (
    CryptoHistoricalDataClient,
    OptionHistoricalDataClient,
    StockHistoricalDataClient,
)

from datadoggo_v3_alpaca.config.settings import Settings, get_settings


def _credentials(settings: Settings) -> tuple[Optional[str], Optional[str]]:
    """設定からAlpaca APIキーとシークレットを取得する."""
    api_key, secret_key = settings.alpaca_credentials
    return api_key, secret_key


class AlpacaClientFactory:
    """Alpaca SDKクライアントを遅延初期化し共有する."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._stock_client: StockHistoricalDataClient | None = None
        self._crypto_client: CryptoHistoricalDataClient | None = None
        self._option_client: OptionHistoricalDataClient | None = None
        self._news_client: NewsClient | None = None

    def stock(self) -> StockHistoricalDataClient:
        """株式ヒストリカルデータクライアントを返す."""
        if self._stock_client is None:
            api_key, secret_key = _credentials(self._settings)
            self._stock_client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key,
                url_override=str(self._settings.alpaca_data_base_url),
            )
        return self._stock_client

    def crypto(self) -> CryptoHistoricalDataClient:
        """暗号資産ヒストリカルデータクライアントを返す."""
        if self._crypto_client is None:
            api_key, secret_key = _credentials(self._settings)
            self._crypto_client = CryptoHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key,
                url_override=str(self._settings.alpaca_data_base_url),
            )
        return self._crypto_client

    def option(self) -> OptionHistoricalDataClient:
        """オプションヒストリカルデータクライアントを返す."""
        if self._option_client is None:
            api_key, secret_key = _credentials(self._settings)
            self._option_client = OptionHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key,
                url_override=str(self._settings.alpaca_data_base_url),
            )
        return self._option_client

    def news(self) -> NewsClient:
        """ニュースAPIクライアントを返す."""
        if self._news_client is None:
            api_key, secret_key = _credentials(self._settings)
            self._news_client = NewsClient(api_key=api_key, secret_key=secret_key)
        return self._news_client
