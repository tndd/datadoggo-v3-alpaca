"""アセット（株式・暗号資産）マスタ取得ロジック."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from typing import Any

import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from pandas import DataFrame

from datadoggo_v3_alpaca.utils.logger import get_logger
from datadoggo_v3_alpaca.utils.retry import alpaca_retry

logger = get_logger(__name__)


@alpaca_retry
def fetch_assets(
    client: TradingClient,
    request: GetAssetsRequest | None = None,
) -> DataFrame:
    """
    指定された条件でアセットリストを取得する（レート制限時は自動リトライ）.

    Parameters
    ----------
    client : TradingClient
        Alpaca Trading APIクライアント
    request : GetAssetsRequest | None
        フィルター条件（Noneの場合は全アセットを取得）

    Returns
    -------
    DataFrame
        取得したアセット情報
    """
    logger.info("fetch_assets_start", request=str(request))

    # Alpaca APIからアセットリストを取得
    assets = client.get_all_assets(request) if request else client.get_all_assets()

    if not assets:
        logger.warning("fetch_assets_empty")
        return pd.DataFrame()

    # アセットオブジェクトを辞書に変換
    records: list[dict[str, Any]] = []
    for asset in assets:
        record = {
            "id": str(asset.id),
            "asset_class": asset.asset_class if hasattr(asset, "asset_class") else asset.class_,
            "exchange": asset.exchange,
            "symbol": asset.symbol,
            "name": getattr(asset, "name", None),
            "status": asset.status,
            "tradable": asset.tradable,
            "marginable": getattr(asset, "marginable", None),
            "shortable": getattr(asset, "shortable", None),
            "easy_to_borrow": getattr(asset, "easy_to_borrow", None),
            "fractionable": getattr(asset, "fractionable", None),
            "options_enabled": getattr(asset, "options_enabled", None),
            "maintenance_margin_requirement": getattr(
                asset, "maintenance_margin_requirement", None
            ),
            "min_order_size": getattr(asset, "min_order_size", None),
            "min_trade_increment": getattr(asset, "min_trade_increment", None),
            "price_increment": getattr(asset, "price_increment", None),
        }
        records.append(record)

    df = pd.DataFrame(records)
    df["source"] = "alpaca"

    logger.info("fetch_assets_success", rows=len(df))
    return df
