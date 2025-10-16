# datadoggo-v3-alpaca

Alpaca SDK (`alpaca-py`) を利用して株式・暗号資産・オプション・ニュースのヒストリカルデータ、およびアセットマスタ・オプション契約マスタを取得し、PostgreSQL (`alpaca` スキーマ) へ保存するツール群です。バッチ実行や将来的なAPI化を見据えて、取得→整形→UPSERTまでをサービスレイヤで統一しています。

## セットアップ
1. `.env.example` をコピーして `.env` を作成する
   - `DATABASE_URL_TEST` は必須。ENVIRONMENTを指定しない場合、この値が `DATABASE_URL` として扱われる
   - ステージングや本番を利用する場合は `DATABASE_URL_STG` / `DATABASE_URL_PROD` を設定し、実行時に `ENVIRONMENT=STG` などを付与
   - 必要に応じて `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`、デフォルト取得シンボル (`DEFAULT_*_SYMBOLS`) を設定
2. 依存関係の同期: `uv sync`
3. Postgresコンテナ (`postgres-docker`) を起動し、必要なら `personal_tracker_test` などのDBを作成

## 使い方

### ヒストリカルデータの取得
- 株式バー取得の例:
  ```bash
  uv run python -m datadoggo_v3_alpaca \
      --kind stock \
      --symbols AAPL,MSFT \
      --timeframe 1Day \
      --start 2024-09-01T00:00:00+00:00
  ```
- 暗号資産バーをステージング環境で取得する例:
  ```bash
  ENVIRONMENT=STG uv run python -m datadoggo_v3_alpaca --kind crypto --symbols BTC/USD --timeframe 1Hour
  ```

### シンボルリスト（マスタ）の同期
Alpaca公式推奨: アセットマスタは毎朝8:20 AM ET以降に1回更新すれば十分

- 全アセット（株式・暗号資産）を取得:
  ```bash
  uv run python -m datadoggo_v3_alpaca --kind sync-assets --asset-class all
  ```
- 株式のみ取得:
  ```bash
  uv run python -m datadoggo_v3_alpaca --kind sync-assets --asset-class us_equity
  ```
- 暗号資産のみ取得:
  ```bash
  uv run python -m datadoggo_v3_alpaca --kind sync-assets --asset-class crypto
  ```
- 特定銘柄のオプション契約リストを取得:
  ```bash
  uv run python -m datadoggo_v3_alpaca --kind sync-options --symbols AAPL,SPY
  ```
- 満期日でフィルタリングしてオプション契約を取得:
  ```bash
  uv run python -m datadoggo_v3_alpaca \
      --kind sync-options \
      --symbols AAPL \
      --expiration-gte 2025-01-01 \
      --expiration-lte 2025-12-31
  ```

実行すると対象データが整形され、PostgreSQLの `alpaca` スキーマ配下へUPSERTされます。

## 設定のポイント
- `ENVIRONMENT` を指定しない場合は自動的に `TEST` とみなし、`DATABASE_URL_TEST` の内容が利用されます
- `ENVIRONMENT=PROD` などを外部から付与すると、対応する `DATABASE_URL_*` で接続します (未設定の場合はエラー)
- 取得するシンボルを `.env` の `DEFAULT_*_SYMBOLS` に記述しておけば、CLI引数を省略可能です

## テスト
```bash
uv run pytest     # DB未整備の場合はrepositoryテストがスキップされます
uv run ruff check
uv run pyright
```
