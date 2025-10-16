"""PostgreSQLへの保存処理."""

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence, cast

import pandas as pd
from pandas import DataFrame, isna
from sqlalchemy import Table, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from datadoggo_v3_alpaca.models import tables
from datadoggo_v3_alpaca.utils.logger import get_logger

logger = get_logger(__name__)


def _to_records(dataframe: DataFrame) -> list[dict[str, Any]]:
    """DataFrameをDB書き込み用の辞書リストへ変換する."""
    rows = cast(list[dict[str, Any]], dataframe.to_dict(orient="records"))
    records: list[dict[str, Any]] = []
    for row in rows:
        normalized: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, pd.Timestamp):
                if value.tzinfo is None:
                    normalized[key] = value.tz_localize("UTC").to_pydatetime()
                else:
                    normalized[key] = value.tz_convert("UTC").to_pydatetime()
            else:
                normalized[key] = value
        records.append(normalized)
    return records


def _normalize_symbols(value: Any) -> list[str]:
    """ニュース記事のsymbols値をリスト化する."""
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, tuple):
        return [str(item) for item in value if item is not None]
    if value is None or (isinstance(value, float) and isna(value)):
        return []
    return [str(value)]


class PostgresRepository:
    """SQLAlchemyを用いたPostgreSQL永続化クラス."""

    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(database_url, echo=False)

    async def ensure_schema(self) -> None:
        """必要なテーブルを作成する."""
        async with self._engine.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {tables.SCHEMA_NAME}"))
            await connection.run_sync(tables.metadata.create_all)
        logger.info("ensure_schema_completed")

    async def upsert_bars(
        self,
        table: Table,
        dataframe: DataFrame,
        conflict_columns: Sequence[str],
    ) -> int:
        """bars系データをUPSERTする."""
        if dataframe.empty:
            return 0

        payload = dataframe.copy()
        if "ingested_at" not in payload.columns:
            payload["ingested_at"] = datetime.now(timezone.utc)

        records = _to_records(payload)
        statement = pg_insert(table).values(records)
        update_columns = {
            column.name: getattr(statement.excluded, column.name)
            for column in table.c
            if column.name not in conflict_columns
        }
        async with self._engine.begin() as connection:
            await connection.execute(
                statement.on_conflict_do_update(
                    index_elements=[table.c[column] for column in conflict_columns],
                    set_=update_columns,
                )
            )
        logger.info("upsert_bars_completed", table=table.name, rows=len(records))
        return len(records)

    async def upsert_news(self, dataframe: DataFrame) -> int:
        """ニュースデータをUPSERTする."""
        if dataframe.empty:
            return 0

        payload = dataframe.copy()
        if "ingested_at" not in payload.columns:
            payload["ingested_at"] = datetime.now(timezone.utc)

        symbols_series = payload["symbols"]
        payload["symbols"] = symbols_series.apply(_normalize_symbols)
        records = _to_records(payload)
        table = tables.news_articles
        statement = pg_insert(table).values(records)
        update_columns = {
            column.name: getattr(statement.excluded, column.name)
            for column in table.c
            if column.name != "id"
        }
        async with self._engine.begin() as connection:
            await connection.execute(
                statement.on_conflict_do_update(
                    index_elements=[table.c["id"]],
                    set_=update_columns,
                )
            )
        logger.info("upsert_news_completed", rows=len(records))
        return len(records)

    async def upsert_assets(self, dataframe: DataFrame) -> int:
        """アセット（株式・暗号資産）マスタをUPSERTする."""
        if dataframe.empty:
            return 0

        payload = dataframe.copy()
        if "ingested_at" not in payload.columns:
            payload["ingested_at"] = datetime.now(timezone.utc)

        records = _to_records(payload)
        table = tables.assets
        statement = pg_insert(table).values(records)
        update_columns = {
            column.name: getattr(statement.excluded, column.name)
            for column in table.c
            if column.name != "id"
        }
        async with self._engine.begin() as connection:
            await connection.execute(
                statement.on_conflict_do_update(
                    index_elements=[table.c["id"]],
                    set_=update_columns,
                )
            )
        logger.info("upsert_assets_completed", rows=len(records))
        return len(records)

    async def upsert_option_contracts(self, dataframe: DataFrame) -> int:
        """オプション契約マスタをUPSERTする."""
        if dataframe.empty:
            return 0

        payload = dataframe.copy()
        if "ingested_at" not in payload.columns:
            payload["ingested_at"] = datetime.now(timezone.utc)

        records = _to_records(payload)
        table = tables.option_contracts
        statement = pg_insert(table).values(records)
        update_columns = {
            column.name: getattr(statement.excluded, column.name)
            for column in table.c
            if column.name != "id"
        }
        async with self._engine.begin() as connection:
            await connection.execute(
                statement.on_conflict_do_update(
                    index_elements=[table.c["id"]],
                    set_=update_columns,
                )
            )
        logger.info("upsert_option_contracts_completed", rows=len(records))
        return len(records)

    async def dispose(self) -> None:
        """Engineをクリーンアップする."""
        await self._engine.dispose()
