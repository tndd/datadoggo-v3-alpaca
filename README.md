## datadoggo-v3-alpaca

Alpaca SDK (`alpaca-py`) を利用して株式・暗号資産・オプション・ニュースのヒストリカルデータを取得し、PostgreSQLへ保存するツール群です。

### セットアップ
1. `.env.example` をコピーして `.env` を作成する
   - `ENVIRONMENT` を `TEST` / `STG` などに設定（未指定時は自動的に `TEST` を使用）
   - `DATABASE_URL_TEST`、必要に応じて `DATABASE_URL_STG` / `DATABASE_URL_PROD` を設定
   - Alpaca APIキー（`ALPACA_API_KEY` / `ALPACA_SECRET_KEY`）を登録
2. 依存関係の同期: `uv sync`

### 実行例
```bash
uv run python -m datadoggo_v3_alpaca --kind stock --symbols AAPL,MSFT --timeframe 1Day --start 2024-09-01T00:00:00+00:00
```

### テスト
```bash
uv run pytest
uv run ruff check
uv run pyright
```
