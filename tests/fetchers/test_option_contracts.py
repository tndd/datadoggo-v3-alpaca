"""fetch_option_contractsの整形結果を検証するテスト群."""

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from alpaca.trading.enums import AssetStatus, ContractType, ExerciseStyle
from alpaca.trading.requests import GetOptionContractsRequest

from datadoggo_v3_alpaca.fetchers.option_contracts import fetch_option_contracts


class DummyOptionContract:
    """Alpaca OptionContract型のダミー実装."""

    def __init__(self, **kwargs: Any) -> None:
        self.id = kwargs.get("id", UUID("12345678-1234-5678-1234-567812345678"))
        self.symbol = kwargs.get("symbol", "AAPL230118C00145000")
        self.name = kwargs.get("name", "AAPL Jan 18 2023 $145 Call")
        self.status = kwargs.get("status", AssetStatus.ACTIVE)
        self.tradable = kwargs.get("tradable", True)
        self.expiration_date = kwargs.get("expiration_date", date(2023, 1, 18))
        self.root_symbol = kwargs.get("root_symbol", "AAPL")
        self.underlying_symbol = kwargs.get("underlying_symbol", "AAPL")
        self.underlying_asset_id = kwargs.get("underlying_asset_id", None)
        self.type = kwargs.get("type", ContractType.CALL)
        self.style = kwargs.get("style", ExerciseStyle.AMERICAN)
        self.strike_price = kwargs.get("strike_price", Decimal("145.0000"))
        self.multiplier = kwargs.get("multiplier", "100")
        self.size = kwargs.get("size", 100)
        self.open_interest = kwargs.get("open_interest", None)
        self.open_interest_date = kwargs.get("open_interest_date", None)
        self.close_price = kwargs.get("close_price", None)
        self.close_price_date = kwargs.get("close_price_date", None)


class DummyOptionContractsResponse:
    """OptionContractsResponse型のダミー実装."""

    def __init__(
        self, option_contracts: list[DummyOptionContract], next_page_token: str | None = None
    ) -> None:
        self.option_contracts = option_contracts
        self.next_page_token = next_page_token


class DummyTradingClient:
    """TradingClient型のダミー実装（オプション契約用）."""

    def __init__(
        self,
        responses: list[DummyOptionContractsResponse],
    ) -> None:
        self._responses = responses
        self._call_count = 0

    def get_option_contracts(
        self, _: GetOptionContractsRequest
    ) -> DummyOptionContractsResponse:  # pragma: no cover - 単純スタブ
        response = self._responses[min(self._call_count, len(self._responses) - 1)]
        self._call_count += 1
        return response


def test_fetch_option_contracts_returns_expected_columns() -> None:
    """
    正常系: オプション契約リストが正しく整形され、必須カラムが揃うことを確認する.

    検証観点:
    - DataFrame化される
    - 必須カラム（id, symbol, expiration_date, strike_price等）が含まれる
    - source='alpaca'が付与される
    """
    contracts = [
        DummyOptionContract(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            symbol="AAPL230118C00145000",
            underlying_symbol="AAPL",
            expiration_date=date(2023, 1, 18),
            strike_price=Decimal("145.0000"),
            type=ContractType.CALL,
        ),
        DummyOptionContract(
            id=UUID("87654321-4321-8765-4321-876543218765"),
            symbol="AAPL230118P00140000",
            underlying_symbol="AAPL",
            expiration_date=date(2023, 1, 18),
            strike_price=Decimal("140.0000"),
            type=ContractType.PUT,
        ),
    ]

    response = DummyOptionContractsResponse(contracts)
    client = DummyTradingClient([response])
    request = GetOptionContractsRequest(underlying_symbols=["AAPL"])
    result = fetch_option_contracts(client, request)

    assert not result.empty
    assert len(result) == 2
    assert set(
        [
            "id",
            "symbol",
            "underlying_symbol",
            "expiration_date",
            "strike_price",
            "type",
            "source",
        ]
    ).issubset(result.columns)
    assert result.loc[0, "source"] == "alpaca"
    assert result.loc[0, "underlying_symbol"] == "AAPL"
    assert result.loc[1, "underlying_symbol"] == "AAPL"
    assert result.loc[0, "type"] == ContractType.CALL
    assert result.loc[1, "type"] == ContractType.PUT


def test_fetch_option_contracts_handles_empty_response() -> None:
    """
    正常系（境界値）: オプション契約が0件の場合、空のDataFrameが返ることを確認する.

    検証観点:
    - 空のリストでもエラーにならない
    - 空のDataFrameが返される
    """
    response = DummyOptionContractsResponse([])
    client = DummyTradingClient([response])
    request = GetOptionContractsRequest(underlying_symbols=["INVALID"])
    result = fetch_option_contracts(client, request)

    assert result.empty


def test_fetch_option_contracts_handles_pagination() -> None:
    """
    正常系: ページネーションが正しく処理されることを確認する.

    検証観点:
    - next_page_tokenがある場合、次のページも取得される
    - 全ページの契約が統合されて返される
    """
    # 1ページ目
    page1_contracts = [
        DummyOptionContract(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            symbol="SPY230118C00400000",
            underlying_symbol="SPY",
        ),
        DummyOptionContract(
            id=UUID("22222222-2222-2222-2222-222222222222"),
            symbol="SPY230118C00405000",
            underlying_symbol="SPY",
        ),
    ]

    # 2ページ目
    page2_contracts = [
        DummyOptionContract(
            id=UUID("33333333-3333-3333-3333-333333333333"),
            symbol="SPY230118C00410000",
            underlying_symbol="SPY",
        ),
    ]

    response1 = DummyOptionContractsResponse(page1_contracts, next_page_token="page2_token")
    response2 = DummyOptionContractsResponse(page2_contracts, next_page_token=None)

    client = DummyTradingClient([response1, response2])
    request = GetOptionContractsRequest(underlying_symbols=["SPY"])
    result = fetch_option_contracts(client, request)

    assert not result.empty
    assert len(result) == 3  # 2ページ分の合計
    assert result.loc[0, "symbol"] == "SPY230118C00400000"
    assert result.loc[1, "symbol"] == "SPY230118C00405000"
    assert result.loc[2, "symbol"] == "SPY230118C00410000"


def test_fetch_option_contracts_includes_optional_fields() -> None:
    """
    正常系: オプショナルなフィールド（open_interest, close_price等）も取得されることを確認する.

    検証観点:
    - open_interest, open_interest_date, close_price等が含まれる
    - 値がNoneの場合も正しく処理される
    """
    contract_with_optional = DummyOptionContract(
        id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
        symbol="TSLA230120C00200000",
        underlying_symbol="TSLA",
        open_interest=5000,
        open_interest_date=date(2023, 1, 17),
        close_price=Decimal("12.50"),
        close_price_date=date(2023, 1, 17),
    )

    response = DummyOptionContractsResponse([contract_with_optional])
    client = DummyTradingClient([response])
    request = GetOptionContractsRequest(underlying_symbols=["TSLA"])
    result = fetch_option_contracts(client, request)

    assert not result.empty
    assert result.loc[0, "open_interest"] == 5000
    assert result.loc[0, "open_interest_date"] == date(2023, 1, 17)
    assert result.loc[0, "close_price"] == Decimal("12.50")
    assert result.loc[0, "close_price_date"] == date(2023, 1, 17)
