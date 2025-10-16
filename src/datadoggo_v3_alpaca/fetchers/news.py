"""ニュースAPI取得ロジック."""

from __future__ import annotations

from typing import Sequence, cast

import pandas as pd
from alpaca.data import NewsClient
from alpaca.data.models.news import NewsSet
from alpaca.data.requests import NewsRequest
from pandas import DataFrame

from datadoggo_v3_alpaca.fetchers._base import ensure_timezone
from datadoggo_v3_alpaca.utils.logger import get_logger
from datadoggo_v3_alpaca.utils.retry import alpaca_retry

logger = get_logger(__name__)


def _normalize_symbols(value: object) -> list[str]:
    """ニュースレスポンスのsymbolsをリストに整形する."""
    if isinstance(value, (list, tuple)):
        items = cast(Sequence[object], value)
        return [str(item) for item in items if item is not None]
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    return [str(value)]


def _default_source(value: object) -> str:
    """ソース名の欠損値を補完する."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "alpaca"
    return str(value)


@alpaca_retry
def fetch_news_articles(
    client: NewsClient,
    request: NewsRequest,
) -> DataFrame:
    """指定された条件でニュースを取得する（レート制限時は自動リトライ）."""
    logger.info(
        "fetch_news_articles_start",
        symbols=request.symbols,
        start=str(request.start),
        end=str(request.end),
        limit=request.limit,
        include_content=request.include_content,
    )

    response = client.get_news(request)
    if isinstance(response, dict):
        dataframe = pd.DataFrame(response.get("news", []))
    else:
        news_set: NewsSet = response
        dataframe = news_set.df.reset_index(drop=True)

    if dataframe.empty:
        logger.warning("fetch_news_articles_empty", symbols=request.symbols)
        return dataframe

    expected_columns = [
        "id",
        "headline",
        "summary",
        "author",
        "url",
        "created_at",
        "updated_at",
        "source",
        "symbols",
    ]

    for column in expected_columns:
        if column not in dataframe.columns:
            dataframe[column] = None

    symbols_series = dataframe["symbols"]
    dataframe["symbols"] = symbols_series.map(_normalize_symbols)
    dataframe["id"] = dataframe["id"].astype(str)
    dataframe["created_at"] = ensure_timezone(dataframe["created_at"])
    dataframe["updated_at"] = ensure_timezone(dataframe["updated_at"])
    source_series = dataframe["source"]
    dataframe["source"] = source_series.map(_default_source)

    logger.info("fetch_news_articles_success", rows=len(dataframe))
    return dataframe[expected_columns]
