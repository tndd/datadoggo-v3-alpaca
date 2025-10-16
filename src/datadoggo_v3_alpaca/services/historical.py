"""ヒストリカルデータ取得から保存までのサービス層."""

from __future__ import annotations

from datetime import datetime, timezone

from alpaca.data.requests import (
    CryptoBarsRequest,
    NewsRequest,
    OptionBarsRequest,
    StockBarsRequest,
)

from datadoggo_v3_alpaca.clients.alpaca import AlpacaClientFactory
from datadoggo_v3_alpaca.config.settings import Settings, get_settings
from datadoggo_v3_alpaca.fetchers.crypto import fetch_crypto_historical
from datadoggo_v3_alpaca.fetchers.news import fetch_news_articles
from datadoggo_v3_alpaca.fetchers.option import fetch_option_historical
from datadoggo_v3_alpaca.fetchers.stock import fetch_stock_historical
from datadoggo_v3_alpaca.models.tables import crypto_bars, option_bars, stock_bars
from datadoggo_v3_alpaca.repository.postgres import PostgresRepository
from datadoggo_v3_alpaca.utils.logger import get_logger

logger = get_logger(__name__)


class HistoricalIngestionService:
    """資産クラスごとのヒストリカルデータ取得フロー."""

    def __init__(
        self,
        repository: PostgresRepository,
        clients: AlpacaClientFactory | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings or get_settings()
        self._clients = clients or AlpacaClientFactory(self._settings)

    async def ingest_stock(self, request: StockBarsRequest) -> int:
        """株式データを取得し保存する."""
        dataframe = fetch_stock_historical(self._clients.stock(), request)
        if dataframe.empty:
            return 0
        dataframe["ingested_at"] = datetime.now(timezone.utc)
        return await self._repository.upsert_bars(
            stock_bars, dataframe, conflict_columns=("symbol", "timestamp", "timeframe")
        )

    async def ingest_crypto(self, request: CryptoBarsRequest) -> int:
        """暗号資産データを取得し保存する."""
        dataframe = fetch_crypto_historical(self._clients.crypto(), request)
        if dataframe.empty:
            return 0
        dataframe["ingested_at"] = datetime.now(timezone.utc)
        return await self._repository.upsert_bars(
            crypto_bars, dataframe, conflict_columns=("symbol", "timestamp", "timeframe")
        )

    async def ingest_option(self, request: OptionBarsRequest) -> int:
        """オプションデータを取得し保存する."""
        dataframe = fetch_option_historical(self._clients.option(), request)
        if dataframe.empty:
            return 0
        dataframe["ingested_at"] = datetime.now(timezone.utc)
        return await self._repository.upsert_bars(
            option_bars, dataframe, conflict_columns=("symbol", "timestamp", "timeframe")
        )

    async def ingest_news(self, request: NewsRequest) -> int:
        """ニュースデータを取得し保存する."""
        dataframe = fetch_news_articles(self._clients.news(), request)
        if dataframe.empty:
            return 0
        dataframe["ingested_at"] = datetime.now(timezone.utc)
        return await self._repository.upsert_news(dataframe)
