"""PostgresRepositoryの振る舞いを検証する."""

from __future__ import annotations

from datetime import datetime, timezone

import asyncpg
import pandas as pd
import pytest
from sqlalchemy import select

from datadoggo_v3_alpaca.config import get_settings
from datadoggo_v3_alpaca.models import tables
from datadoggo_v3_alpaca.repository import PostgresRepository


@pytest.mark.asyncio
async def test_upsert_bars_inserts_and_updates() -> None:
    """正常系: UPSERT処理でデータが挿入され、更新でも件数が変化しないことを確認する."""
    settings = get_settings()
    database_url = settings.async_test_database_url or settings.async_database_url
    repository = PostgresRepository(database_url)
    try:
        await repository.ensure_schema()
    except asyncpg.InvalidCatalogNameError:
        pytest.skip("テスト用データベースが存在しないためスキップ")

    dataframe = pd.DataFrame(
        {
            "symbol": ["TEST"],
            "timestamp": [pd.Timestamp("2024-01-01T00:00:00+00:00")],
            "timeframe": ["1Day"],
            "open": [100.0],
            "high": [105.0],
            "low": [99.0],
            "close": [102.0],
            "volume": [1000.0],
            "trade_count": [10],
            "vw": [101.0],
            "source": ["alpaca"],
            "ingested_at": [datetime.now(timezone.utc)],
        }
    )

    rows = await repository.upsert_bars(
        tables.stock_bars,
        dataframe,
        conflict_columns=("symbol", "timestamp", "timeframe"),
    )
    assert rows == 1

    async with repository._engine.begin() as connection:  # type: ignore[attr-defined]
        result = await connection.execute(
            select(tables.stock_bars).where(tables.stock_bars.c.symbol == "TEST")
        )
        inserted = result.first()
    assert inserted is not None
    assert inserted.symbol == "TEST"

    # 同じデータで再度UPSERTしても件数は1のまま
    rows_again = await repository.upsert_bars(
        tables.stock_bars,
        dataframe,
        conflict_columns=("symbol", "timestamp", "timeframe"),
    )
    assert rows_again == 1

    async with repository._engine.begin() as connection:  # type: ignore[attr-defined]
        await connection.execute(tables.stock_bars.delete().where(tables.stock_bars.c.symbol == "TEST"))

    await repository.dispose()
