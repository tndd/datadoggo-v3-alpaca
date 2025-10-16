## datadoggo-v3-alpaca

Alpaca SDK (`alpaca-py`) を利用して株式・暗号資産・オプション・ニュースのヒストリカルデータを取得し、PostgreSQLへ保存するツール群です。

### セットアップ
1. `.env` に `DATABASE_URL` / `TEST_DATABASE_URL` / `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` などを設定する
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
