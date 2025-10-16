"""株式ヒストリカルデータ取得ロジック."""

from __future__ import annotations

from typing import Any, cast

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.models import BarSet
from alpaca.data.requests import StockBarsRequest
from pandas import DataFrame

from datadoggo_v3_alpaca.fetchers._base import prepare_bars_dataframe
from datadoggo_v3_alpaca.utils.logger import get_logger
from datadoggo_v3_alpaca.utils.retry import alpaca_retry

logger = get_logger(__name__)


@alpaca_retry
def fetch_stock_historical(
    client: StockHistoricalDataClient,
    request: StockBarsRequest,
) -> DataFrame:
    """指定された条件で株式バーを取得する（レート制限時は自動リトライ）."""
    logger.info(
        "fetch_stock_historical_start",
        symbols=request.symbol_or_symbols,
        start=str(request.start),
        end=str(request.end),
        timeframe=str(request.timeframe),
    )

    raw_response = client.get_stock_bars(request)
    if hasattr(raw_response, "df"):
        bar_like = cast(Any, raw_response)
        dataframe = prepare_bars_dataframe(bar_like.df, str(request.timeframe))
    else:
        bar_set = raw_response if isinstance(raw_response, BarSet) else BarSet(raw_response)
        dataframe = prepare_bars_dataframe(bar_set.df, str(request.timeframe))

    if dataframe.empty:
        logger.warning("fetch_stock_historical_empty", symbols=request.symbol_or_symbols)
        return dataframe

    dataframe["source"] = "alpaca"
    logger.info("fetch_stock_historical_success", rows=len(dataframe))
    return dataframe
