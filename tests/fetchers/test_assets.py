"""fetch_assetsの整形結果を検証するテスト群."""

from typing import Any
from uuid import UUID

from alpaca.trading.enums import AssetClass, AssetExchange, AssetStatus
from alpaca.trading.requests import GetAssetsRequest

from datadoggo_v3_alpaca.fetchers.assets import fetch_assets


class DummyAsset:
    """Alpaca Asset型のダミー実装."""

    def __init__(self, **kwargs: Any) -> None:
        self.id = kwargs.get("id", UUID("12345678-1234-5678-1234-567812345678"))
        # asset_classとclass_の両方をサポート（Alpaca SDKの実装に依存）
        self.class_ = kwargs.get("class_", AssetClass.US_EQUITY)
        # asset_classはclass_と同じ値を返すプロパティとして実装
        if "asset_class" in kwargs:
            self.asset_class = kwargs["asset_class"]
        else:
            # hastattrでチェックされるので、属性として存在させる
            self.asset_class = self.class_
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
        self.maintenance_margin_requirement = kwargs.get("maintenance_margin_requirement", None)
        self.min_order_size = kwargs.get("min_order_size", "1")
        self.min_trade_increment = kwargs.get("min_trade_increment", "0.01")
        self.price_increment = kwargs.get("price_increment", "0.01")


class DummyTradingClient:
    """TradingClient型のダミー実装."""

    def __init__(self, assets: list[DummyAsset]) -> None:
        self._assets = assets

    def get_all_assets(
        self, _: GetAssetsRequest | None = None
    ) -> list[DummyAsset]:  # pragma: no cover - 単純スタブ
        return self._assets


def test_fetch_assets_returns_expected_columns() -> None:
    """
    正常系: アセットリストが正しく整形され、必須カラムが揃うことを確認する.

    検証観点:
    - DataFrame化される
    - 必須カラム（id, asset_class, symbol, tradable等）が含まれる
    - source='alpaca'が付与される
    """
    assets = [
        DummyAsset(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            symbol="AAPL",
            name="Apple Inc",
            tradable=True,
            options_enabled=True,
        ),
        DummyAsset(
            id=UUID("87654321-4321-8765-4321-876543218765"),
            symbol="MSFT",
            name="Microsoft Corporation",
            tradable=True,
            options_enabled=False,
        ),
    ]

    client = DummyTradingClient(assets)
    result = fetch_assets(client, request=None)

    assert not result.empty
    assert len(result) == 2
    assert set(
        [
            "id",
            "asset_class",
            "exchange",
            "symbol",
            "name",
            "status",
            "tradable",
            "source",
        ]
    ).issubset(result.columns)
    assert result.loc[0, "source"] == "alpaca"
    assert result.loc[0, "symbol"] == "AAPL"
    assert result.loc[1, "symbol"] == "MSFT"
    assert result.loc[0, "tradable"] == True  # noqa: E712
    assert result.loc[0, "options_enabled"] == True  # noqa: E712
    assert result.loc[1, "options_enabled"] == False  # noqa: E712


def test_fetch_assets_handles_empty_response() -> None:
    """
    正常系（境界値）: アセットが0件の場合、空のDataFrameが返ることを確認する.

    検証観点:
    - 空のリストでもエラーにならない
    - 空のDataFrameが返される
    """
    client = DummyTradingClient([])
    result = fetch_assets(client, request=None)

    assert result.empty


def test_fetch_assets_handles_crypto_asset_class() -> None:
    """
    正常系: 暗号資産のアセットも正しく処理されることを確認する.

    検証観点:
    - class_属性がAssetClass.CRYPTOの場合も正しく変換される
    - min_order_sizeなどの暗号資産特有のフィールドも取得される
    """
    crypto_asset = DummyAsset(
        id=UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        class_=AssetClass.CRYPTO,
        symbol="BTC/USD",
        name="Bitcoin/USD",
        exchange=AssetExchange.CRYPTO,
        tradable=True,
        fractionable=True,
        min_order_size="0.0001",
        min_trade_increment="0.0001",
        price_increment="1",
    )

    client = DummyTradingClient([crypto_asset])
    result = fetch_assets(client, request=None)

    assert not result.empty
    assert result.loc[0, "symbol"] == "BTC/USD"
    assert result.loc[0, "asset_class"] == AssetClass.CRYPTO
    assert result.loc[0, "fractionable"] == True  # noqa: E712
    assert result.loc[0, "min_order_size"] == "0.0001"
