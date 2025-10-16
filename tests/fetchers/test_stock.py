"""fetch_stock_historicalの整形結果を検証するテスト群."""

import pandas as pd
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from datadoggo_v3_alpaca.fetchers.stock import fetch_stock_historical


class DummyStockResponse:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df


class DummyStockClient:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def get_stock_bars(self, _: StockBarsRequest) -> DummyStockResponse:  # pragma: no cover - 単純スタブ
        return DummyStockResponse(self._df)


def test_fetch_stock_historical_returns_expected_columns() -> None:
    """正常系: MultiIndexのDataFrameが整形され、共通カラムが追加されることを確認する."""
    index = pd.MultiIndex.from_tuples(
        [("AAPL", pd.Timestamp("2024-01-01T00:00:00+00:00"))],
        names=["symbol", "timestamp"],
    )
    df = pd.DataFrame(
        {
            "open": [190.0],
            "high": [192.0],
            "low": [189.5],
            "close": [191.2],
            "volume": [1_000_000],
            "trade_count": [4500],
            "vw": [191.0],
        },
        index=index,
    )

    request = StockBarsRequest(
        symbol_or_symbols=["AAPL"],
        timeframe=TimeFrame(1, TimeFrameUnit.Day),
        start=None,
        end=None,
    )

    client = DummyStockClient(df)
    result = fetch_stock_historical(client, request)

    assert not result.empty
    assert set(["symbol", "timestamp", "open", "close", "timeframe", "source"]).issubset(result.columns)
    assert result.loc[0, "timeframe"] == "1Day"
    assert result.loc[0, "source"] == "alpaca"
    assert str(result.loc[0, "timestamp"].tzinfo) in ("UTC", "UTC")
