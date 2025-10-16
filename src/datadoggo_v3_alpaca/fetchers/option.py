"""オプションヒストリカルデータ取得ロジック."""

from __future__ import annotations

from typing import Any, cast

from alpaca.data.historical import OptionHistoricalDataClient
from alpaca.data.models import BarSet
from alpaca.data.requests import OptionBarsRequest
from pandas import DataFrame

from datadoggo_v3_alpaca.fetchers._base import prepare_bars_dataframe
from datadoggo_v3_alpaca.utils.logger import get_logger

logger = get_logger(__name__)


def fetch_option_historical(
    client: OptionHistoricalDataClient,
    request: OptionBarsRequest,
) -> DataFrame:
    """指定された条件でオプションバーを取得する."""
    logger.info(
        "fetch_option_historical_start",
        symbols=request.symbol_or_symbols,
        start=str(request.start),
        end=str(request.end),
        timeframe=str(request.timeframe),
    )

    raw_response = client.get_option_bars(request)
    if hasattr(raw_response, "df"):
        bar_like = cast(Any, raw_response)
        dataframe = prepare_bars_dataframe(bar_like.df, str(request.timeframe))
    else:
        bar_set = raw_response if isinstance(raw_response, BarSet) else BarSet(raw_response)
        dataframe = prepare_bars_dataframe(bar_set.df, str(request.timeframe))

    if dataframe.empty:
        logger.warning("fetch_option_historical_empty", symbols=request.symbol_or_symbols)
        return dataframe

    if "open_interest" not in dataframe.columns:
        dataframe["open_interest"] = 0
    if "underlying_symbol" not in dataframe.columns:
        dataframe["underlying_symbol"] = None

    dataframe["source"] = "alpaca"
    logger.info("fetch_option_historical_success", rows=len(dataframe))
    return dataframe
