"""fetch_news_articlesの整形処理を検証する."""

import pandas as pd
from alpaca.data.requests import NewsRequest

from datadoggo_v3_alpaca.fetchers.news import fetch_news_articles


class DummyNewsResponse:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df


class DummyNewsClient:
    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def get_news(self, _: NewsRequest) -> DummyNewsResponse:  # pragma: no cover - 単純スタブ
        return DummyNewsResponse(self._df)


def test_fetch_news_articles_normalizes_columns() -> None:
    """正常系: symbolsが配列化され、必須カラムが揃うことを確認する."""
    df = pd.DataFrame(
        {
            "id": [12345],
            "headline": ["Sample Headline"],
            "summary": ["Summary"],
            "author": ["Reporter"],
            "url": ["https://example.com/article"],
            "created_at": ["2024-01-01T00:00:00Z"],
            "updated_at": ["2024-01-01T01:00:00Z"],
            "source": ["alpaca"],
            "symbols": [["AAPL", "MSFT"]],
        }
    )

    request = NewsRequest(symbols="AAPL", limit=10)
    client = DummyNewsClient(df)

    result = fetch_news_articles(client, request)

    assert not result.empty
    assert list(result.columns) == [
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
    assert isinstance(result.loc[0, "symbols"], list)
    assert result.loc[0, "id"] == "12345"
    assert str(result.loc[0, "created_at"].tzinfo) in ("UTC", "UTC")
    assert str(result.loc[0, "updated_at"].tzinfo) in ("UTC", "UTC")
