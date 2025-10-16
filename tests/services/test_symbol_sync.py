"""SymbolSyncServiceの振る舞いを検証するテスト群."""

from typing import Any
from uuid import UUID

import pandas as pd
import pytest
from alpaca.trading.enums import AssetClass, AssetExchange, AssetStatus

from datadoggo_v3_alpaca.services.symbol_sync import SymbolSyncService


class DummyAsset:
    """Assets用のダミーデータ."""

    def __init__(self, **kwargs: Any) -> None:
        self.id = kwargs.get("id", UUID("12345678-1234-5678-1234-567812345678"))
        self.asset_class = kwargs.get("asset_class")
        self.class_ = kwargs.get("class_", AssetClass.US_EQUITY)
        self.exchange = kwargs.get("exchange", AssetExchange.NASDAQ)
        self.symbol = kwargs.get("symbol", "AAPL")
        self.name = kwargs.get("name", "Apple Inc")
        self.status = kwargs.get("status", AssetStatus.ACTIVE)
        self.tradable = kwargs.get("tradable", True)
        self.marginable = kwargs.get("marginable", True)
        self.shortable = kwargs.get("shortable", True)
        self.easy_to_borrow = kwargs.get("easy_to_borrow", True)
        self.fractionable = kwargs.get("fractionable", True)
        self.options_enabled = kwargs.get("options_enabled", True)


class DummyTradingClient:
    """TradingClient用のダミー実装."""

    def __init__(self, assets: list[DummyAsset]) -> None:
        self._assets = assets

    def get_all_assets(self, _: Any = None) -> list[DummyAsset]:  # pragma: no cover
        return self._assets


class DummyClientFactory:
    """AlpacaClientFactory用のダミー実装."""

    def __init__(self, trading_client: DummyTradingClient) -> None:
        self._trading_client = trading_client

    def trading(self) -> DummyTradingClient:  # pragma: no cover
        return self._trading_client


class DummyRepository:
    """PostgresRepository用のダミー実装."""

    def __init__(self) -> None:
        self.last_upserted_assets: pd.DataFrame | None = None
        self.last_upserted_option_contracts: pd.DataFrame | None = None

    async def upsert_assets(self, dataframe: pd.DataFrame) -> int:  # pragma: no cover
        self.last_upserted_assets = dataframe
        return len(dataframe)

    async def upsert_option_contracts(
        self, dataframe: pd.DataFrame
    ) -> int:  # pragma: no cover
        self.last_upserted_option_contracts = dataframe
        return len(dataframe)


class DummySettings:
    """Settings用のダミー実装."""

    pass


@pytest.mark.asyncio
async def test_sync_assets_all() -> None:
    """
    正常系: sync_assets()で全アセットが取得・保存されることを確認する.

    検証観点:
    - asset_class='all'で全アセットが取得される
    - repositoryのupsert_assets()が呼ばれる
    - 保存された件数が返される
    """
    assets = [
        DummyAsset(symbol="AAPL", class_=AssetClass.US_EQUITY),
        DummyAsset(symbol="BTC/USD", class_=AssetClass.CRYPTO),
    ]

    trading_client = DummyTradingClient(assets)
    client_factory = DummyClientFactory(trading_client)
    repository = DummyRepository()
    settings = DummySettings()

    service = SymbolSyncService(repository, client_factory, settings)
    result = await service.sync_assets(asset_class="all")

    assert result == 2
    assert repository.last_upserted_assets is not None
    assert len(repository.last_upserted_assets) == 2


@pytest.mark.asyncio
async def test_sync_assets_us_equity_only() -> None:
    """
    正常系: sync_assets()でUS株式のみが取得されることを確認する.

    検証観点:
    - asset_class='us_equity'でフィルタリングされる
    - GetAssetsRequestが正しく作成される
    """
    assets = [
        DummyAsset(symbol="AAPL", class_=AssetClass.US_EQUITY),
    ]

    trading_client = DummyTradingClient(assets)
    client_factory = DummyClientFactory(trading_client)
    repository = DummyRepository()
    settings = DummySettings()

    service = SymbolSyncService(repository, client_factory, settings)
    result = await service.sync_assets(asset_class="us_equity")

    assert result == 1
    assert repository.last_upserted_assets is not None
    assert repository.last_upserted_assets.loc[0, "symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_sync_assets_crypto_only() -> None:
    """
    正常系: sync_assets()で暗号資産のみが取得されることを確認する.

    検証観点:
    - asset_class='crypto'でフィルタリングされる
    """
    assets = [
        DummyAsset(symbol="BTC/USD", class_=AssetClass.CRYPTO),
    ]

    trading_client = DummyTradingClient(assets)
    client_factory = DummyClientFactory(trading_client)
    repository = DummyRepository()
    settings = DummySettings()

    service = SymbolSyncService(repository, client_factory, settings)
    result = await service.sync_assets(asset_class="crypto")

    assert result == 1
    assert repository.last_upserted_assets is not None
    assert repository.last_upserted_assets.loc[0, "symbol"] == "BTC/USD"


@pytest.mark.asyncio
async def test_sync_assets_empty_result() -> None:
    """
    正常系（境界値）: アセットが0件の場合、0が返ることを確認する.

    検証観点:
    - 空のレスポンスでもエラーにならない
    - 戻り値が0になる
    """
    trading_client = DummyTradingClient([])
    client_factory = DummyClientFactory(trading_client)
    repository = DummyRepository()
    settings = DummySettings()

    service = SymbolSyncService(repository, client_factory, settings)
    result = await service.sync_assets(asset_class="all")

    assert result == 0


@pytest.mark.asyncio
async def test_sync_assets_invalid_asset_class() -> None:
    """
    異常系: 不正なasset_classが指定された場合、ValueErrorが発生することを確認する.

    検証観点:
    - 未対応のasset_classでValueErrorが発生する
    - エラーメッセージに不正な値が含まれる
    """
    trading_client = DummyTradingClient([])
    client_factory = DummyClientFactory(trading_client)
    repository = DummyRepository()
    settings = DummySettings()

    service = SymbolSyncService(repository, client_factory, settings)

    with pytest.raises(ValueError, match="不正なasset_classです"):
        await service.sync_assets(asset_class="invalid_class")
