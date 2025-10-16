"""シンボルリスト同期サービス."""

from __future__ import annotations

from alpaca.trading.enums import AssetClass
from alpaca.trading.requests import GetAssetsRequest, GetOptionContractsRequest

from datadoggo_v3_alpaca.clients.alpaca import AlpacaClientFactory
from datadoggo_v3_alpaca.config.settings import Settings
from datadoggo_v3_alpaca.fetchers.assets import fetch_assets
from datadoggo_v3_alpaca.fetchers.option_contracts import fetch_option_contracts
from datadoggo_v3_alpaca.repository.postgres import PostgresRepository
from datadoggo_v3_alpaca.utils.logger import get_logger

logger = get_logger(__name__)


class SymbolSyncService:
    """
    Alpacaからシンボルリスト（Assets・Option Contracts）を取得してDBに保存する.

    Alpaca公式推奨: Assetsは毎朝8:20 AM ET以降に1回更新すれば十分
    """

    def __init__(
        self,
        repository: PostgresRepository,
        client_factory: AlpacaClientFactory,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._client_factory = client_factory
        self._settings = settings

    async def sync_assets(self, asset_class: str | None = None) -> int:
        """
        アセットリストを取得してDBに同期する.

        Parameters
        ----------
        asset_class : str | None
            "us_equity", "crypto", "all" のいずれか。Noneまたは"all"の場合は全件取得

        Returns
        -------
        int
            保存した件数
        """
        logger.info("sync_assets_start", asset_class=asset_class)

        trading_client = self._client_factory.trading()

        # asset_classに応じてフィルター条件を作成
        if asset_class is None or asset_class == "all":
            # 全アセットを取得
            df = fetch_assets(trading_client, request=None)
        elif asset_class == "us_equity":
            request = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
            df = fetch_assets(trading_client, request)
        elif asset_class == "crypto":
            request = GetAssetsRequest(asset_class=AssetClass.CRYPTO)
            df = fetch_assets(trading_client, request)
        else:
            raise ValueError(f"不正なasset_classです: {asset_class}")

        if df.empty:
            logger.warning("sync_assets_no_data")
            return 0

        rows = await self._repository.upsert_assets(df)
        logger.info("sync_assets_completed", asset_class=asset_class, rows=rows)
        return rows

    async def sync_option_contracts(
        self,
        underlying_symbols: list[str],
        expiration_date_gte: str | None = None,
        expiration_date_lte: str | None = None,
    ) -> int:
        """
        オプション契約リストを取得してDBに同期する.

        Parameters
        ----------
        underlying_symbols : list[str]
            原資産シンボルリスト（例: ["AAPL", "SPY"]）
        expiration_date_gte : str | None
            満期日の下限（YYYY-MM-DD形式）
        expiration_date_lte : str | None
            満期日の上限（YYYY-MM-DD形式）

        Returns
        -------
        int
            保存した件数
        """
        logger.info(
            "sync_option_contracts_start",
            underlying_symbols=underlying_symbols,
            expiration_date_gte=expiration_date_gte,
            expiration_date_lte=expiration_date_lte,
        )

        trading_client = self._client_factory.trading()

        request = GetOptionContractsRequest(
            underlying_symbols=underlying_symbols,
            expiration_date_gte=expiration_date_gte,
            expiration_date_lte=expiration_date_lte,
        )

        df = fetch_option_contracts(trading_client, request)

        if df.empty:
            logger.warning("sync_option_contracts_no_data")
            return 0

        rows = await self._repository.upsert_option_contracts(df)
        logger.info("sync_option_contracts_completed", rows=rows)
        return rows
