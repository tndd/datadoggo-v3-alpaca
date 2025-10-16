"""フェッチ処理で共通利用するユーティリティ."""

from __future__ import annotations

import pandas as pd
from pandas import DataFrame, Series


def prepare_bars_dataframe(df: DataFrame, timeframe: str) -> DataFrame:
    """barsレスポンスを正規化し共通カラムを付与する."""
    if df.empty:
        empty_columns = [
            "symbol",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "trade_count",
            "vw",
            "timeframe",
        ]
        return pd.DataFrame({column: [] for column in empty_columns})
    normalized = df.reset_index().copy()
    if "timestamp" in normalized.columns:
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], errors="coerce", utc=True)
    normalized["timeframe"] = timeframe
    return normalized


def ensure_timezone(series: Series) -> Series:
    """ニュースデータなどのタイムスタンプ列をUTCに統一する."""
    converted = pd.to_datetime(series, errors="coerce", utc=True)
    return converted
