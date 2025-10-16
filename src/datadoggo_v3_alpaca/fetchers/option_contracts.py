"""オプション契約マスタ取得ロジック."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from typing import Any

import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetOptionContractsRequest
from pandas import DataFrame

from datadoggo_v3_alpaca.utils.logger import get_logger
from datadoggo_v3_alpaca.utils.retry import alpaca_retry

logger = get_logger(__name__)


@alpaca_retry
def fetch_option_contracts(
    client: TradingClient,
    request: GetOptionContractsRequest,
) -> DataFrame:
    """
    指定された条件でオプション契約リストを取得する（レート制限時は自動リトライ）.

    Parameters
    ----------
    client : TradingClient
        Alpaca Trading APIクライアント
    request : GetOptionContractsRequest
        フィルター条件（underlying_symbolsは必須）

    Returns
    -------
    DataFrame
        取得したオプション契約情報
    """
    logger.info(
        "fetch_option_contracts_start",
        underlying_symbols=request.underlying_symbols,
        expiration_date_gte=str(request.expiration_date_gte),
        expiration_date_lte=str(request.expiration_date_lte),
    )

    # Alpaca APIからオプション契約リストを取得
    response = client.get_option_contracts(request)

    # ページネーション対応: すべてのページを取得
    all_contracts = list(response.option_contracts) if hasattr(response, "option_contracts") else []
    next_page_token = getattr(response, "next_page_token", None)

    # 追加ページがある場合は取得を続ける
    while next_page_token:
        request.page_token = next_page_token
        response = client.get_option_contracts(request)
        if hasattr(response, "option_contracts"):
            all_contracts.extend(response.option_contracts)
        next_page_token = getattr(response, "next_page_token", None)

    if not all_contracts:
        logger.warning("fetch_option_contracts_empty")
        return pd.DataFrame()

    # オプション契約オブジェクトを辞書に変換
    records: list[dict[str, Any]] = []
    for contract in all_contracts:
        record = {
            "id": str(contract.id),
            "symbol": contract.symbol,
            "name": getattr(contract, "name", None),
            "status": contract.status,
            "tradable": contract.tradable,
            "expiration_date": contract.expiration_date,
            "root_symbol": contract.root_symbol,
            "underlying_symbol": contract.underlying_symbol,
            "underlying_asset_id": str(getattr(contract, "underlying_asset_id", None))
            if getattr(contract, "underlying_asset_id", None)
            else None,
            "type": contract.type,
            "style": getattr(contract, "style", None),
            "strike_price": contract.strike_price,
            "multiplier": str(getattr(contract, "multiplier", None)),
            "size": getattr(contract, "size", None),
            "open_interest": getattr(contract, "open_interest", None),
            "open_interest_date": getattr(contract, "open_interest_date", None),
            "close_price": getattr(contract, "close_price", None),
            "close_price_date": getattr(contract, "close_price_date", None),
        }
        records.append(record)

    df = pd.DataFrame(records)
    df["source"] = "alpaca"

    logger.info("fetch_option_contracts_success", rows=len(df))
    return df
