"""ヒストリカルデータ取得関数の公開モジュール."""

from datadoggo_v3_alpaca.fetchers.crypto import fetch_crypto_historical
from datadoggo_v3_alpaca.fetchers.news import fetch_news_articles
from datadoggo_v3_alpaca.fetchers.option import fetch_option_historical
from datadoggo_v3_alpaca.fetchers.stock import fetch_stock_historical

__all__ = [
    "fetch_stock_historical",
    "fetch_crypto_historical",
    "fetch_option_historical",
    "fetch_news_articles",
]
