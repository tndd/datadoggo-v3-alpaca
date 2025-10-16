"""CLIからヒストリカルデータ取得タスクを実行する."""

from __future__ import annotations

import argparse
import asyncio
import re
from datetime import datetime, timezone
from typing import Sequence

from alpaca.data.requests import (
    CryptoBarsRequest,
    NewsRequest,
    OptionBarsRequest,
    StockBarsRequest,
)
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

from datadoggo_v3_alpaca.clients.alpaca import AlpacaClientFactory
from datadoggo_v3_alpaca.config.settings import Settings, get_settings
from datadoggo_v3_alpaca.repository.postgres import PostgresRepository
from datadoggo_v3_alpaca.services.historical import HistoricalIngestionService
from datadoggo_v3_alpaca.services.symbol_sync import SymbolSyncService
from datadoggo_v3_alpaca.utils.logger import configure_logging, get_logger

logger = get_logger(__name__)

TIMEFRAME_PATTERN = re.compile(r"^(?P<amount>\d+)\s*(?P<unit>[a-zA-Z]+)$")


def parse_timeframe(value: str) -> TimeFrame:
    """TimeFrame形式の文字列をパースする."""
    match = TIMEFRAME_PATTERN.match(value)
    if not match:
        raise ValueError(f"不正なtimeframe指定です: {value}")
    amount = int(match.group("amount"))
    unit_key = match.group("unit").lower()

    unit_map: dict[str, str] = {
        "min": "Minute",
        "mins": "Minute",
        "minute": "Minute",
        "minutes": "Minute",
        "hour": "Hour",
        "hours": "Hour",
        "day": "Day",
        "days": "Day",
        "week": "Week",
        "weeks": "Week",
        "month": "Month",
        "months": "Month",
    }

    if unit_key not in unit_map:
        raise ValueError(f"不正なtimeframe単位です: {value}")

    unit_value = TimeFrameUnit(unit_map[unit_key])
    return TimeFrame(amount, unit_value)


def parse_datetime(value: str | None) -> datetime | None:
    """ISO8601形式の日時文字列をパースする."""
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def split_symbols(raw: str | Sequence[str] | None) -> list[str]:
    """シンボルリストを生成する."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [symbol.strip() for symbol in raw.split(",") if symbol.strip()]
    return [symbol.strip() for symbol in raw if symbol.strip()]


def build_stock_request(settings: Settings, args: argparse.Namespace) -> StockBarsRequest:
    symbols = split_symbols(args.symbols) or settings.default_stock_symbols
    if not symbols:
        raise ValueError("株式シンボルが指定されていません。")
    return StockBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=parse_timeframe(args.timeframe),
        start=parse_datetime(args.start),
        end=parse_datetime(args.end),
        limit=args.limit,
    )


def build_crypto_request(settings: Settings, args: argparse.Namespace) -> CryptoBarsRequest:
    symbols = split_symbols(args.symbols) or settings.default_crypto_symbols
    if not symbols:
        raise ValueError("暗号資産シンボルが指定されていません。")
    return CryptoBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=parse_timeframe(args.timeframe),
        start=parse_datetime(args.start),
        end=parse_datetime(args.end),
        limit=args.limit,
    )


def build_option_request(settings: Settings, args: argparse.Namespace) -> OptionBarsRequest:
    symbols = split_symbols(args.symbols) or settings.default_option_symbols
    if not symbols:
        raise ValueError("オプション銘柄が指定されていません。")
    return OptionBarsRequest(
        symbol_or_symbols=symbols,
        timeframe=parse_timeframe(args.timeframe),
        start=parse_datetime(args.start),
        end=parse_datetime(args.end),
        limit=args.limit,
    )


def build_news_request(settings: Settings, args: argparse.Namespace) -> NewsRequest:
    symbols = split_symbols(args.symbols) or settings.default_news_symbols
    return NewsRequest(
        symbols=",".join(symbols) if symbols else None,
        start=parse_datetime(args.start),
        end=parse_datetime(args.end),
        limit=args.limit,
        include_content=args.include_content,
        exclude_contentless=args.exclude_contentless,
    )


async def execute_task(kind: str, settings: Settings, args: argparse.Namespace) -> int:
    """指定kindに応じて取得処理を実行する."""
    repository = PostgresRepository(settings.async_database_url)
    client_factory = AlpacaClientFactory(settings)
    await repository.ensure_schema()

    try:
        # ヒストリカルデータ取得
        if kind in ("stock", "crypto", "option", "news"):
            service = HistoricalIngestionService(repository, client_factory, settings)
            if kind == "stock":
                request = build_stock_request(settings, args)
                return await service.ingest_stock(request)
            if kind == "crypto":
                request = build_crypto_request(settings, args)
                return await service.ingest_crypto(request)
            if kind == "option":
                request = build_option_request(settings, args)
                return await service.ingest_option(request)
            if kind == "news":
                request = build_news_request(settings, args)
                return await service.ingest_news(request)

        # シンボルリスト同期
        if kind == "sync-assets":
            sync_service = SymbolSyncService(repository, client_factory, settings)
            asset_class = getattr(args, "asset_class", None)
            return await sync_service.sync_assets(asset_class)

        if kind == "sync-options":
            sync_service = SymbolSyncService(repository, client_factory, settings)
            symbols = split_symbols(args.symbols)
            if not symbols:
                raise ValueError("オプション契約同期には--symbolsが必須です")
            expiration_gte = getattr(args, "expiration_gte", None)
            expiration_lte = getattr(args, "expiration_lte", None)
            return await sync_service.sync_option_contracts(
                underlying_symbols=symbols,
                expiration_date_gte=expiration_gte,
                expiration_date_lte=expiration_lte,
            )

        raise ValueError(f"未対応のkindです: {kind}")
    finally:
        await repository.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Alpacaヒストリカルデータ取得タスク")
    parser.add_argument(
        "--kind",
        choices=["stock", "crypto", "option", "news", "sync-assets", "sync-options"],
        required=True,
        help="実行するタスクの種類",
    )
    parser.add_argument("--symbols", help="カンマ区切りのシンボルリスト")
    parser.add_argument("--timeframe", default="1Day", help="例: 1Day / 1Hour / 5Min")
    parser.add_argument("--start", help="ISO8601形式の開始日時 (例: 2024-01-01T00:00:00+00:00)")
    parser.add_argument("--end", help="ISO8601形式の終了日時")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--include-content", action="store_true", dest="include_content")
    parser.add_argument("--exclude-contentless", action="store_true", dest="exclude_contentless")

    # sync-assets用オプション
    parser.add_argument(
        "--asset-class",
        choices=["us_equity", "crypto", "all"],
        help="sync-assets使用時: 取得するアセットクラス",
    )

    # sync-options用オプション
    parser.add_argument("--expiration-gte", dest="expiration_gte", help="満期日の下限 (YYYY-MM-DD)")
    parser.add_argument("--expiration-lte", dest="expiration_lte", help="満期日の上限 (YYYY-MM-DD)")

    return parser


def main() -> None:
    configure_logging()
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()

    try:
        rows = asyncio.run(execute_task(args.kind, settings, args))
    except Exception as exc:  # noqa: BLE001
        logger.error("fetch_task_failed", error=str(exc))
        raise SystemExit(1) from exc

    logger.info("fetch_task_completed", kind=args.kind, rows=rows)


if __name__ == "__main__":
    main()
