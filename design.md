# datadoggo-v3-alpaca
alpaca sdkを利用してヒストリカルデータを取得し、永続化および将来的なAPI化を行うための設計ドキュメント。
ちなみにpostgresはdocker上のpostgres-dockerコンテナを前提とした設計です。

## 目的と背景
- AlpacaのMarket Data APIから株式・暗号資産・オプション・ニュースのヒストリカルデータを取得し、継続的に分析・監視に活用できる形で保存する。citeturn1search1
- オプションデータは2024年2月以降が利用可能なため、設計時にデータ可用性の制約を考慮する。citeturn1search0
- 将来的にこれらの取得タスクを外部公開APIとして提供し、自動バッチやオンデマンド実行を可能にする。

## フェーズ1のスコープ
1. Alpaca SDK（`alpaca-py`）の各ヒストリカルデータクライアントを用いた取得関数の整備  
   - `fetch_stock_historical`
   - `fetch_crypto_historical`
   - `fetch_option_historical`
   - `fetch_news_articles`
2. 取得データを正規化し、PostgreSQL（dockerの`postgres-docker`コンテナ）へ保存するDAO層の整備
3. 共通タスクオーケストレーション（バッチ実行スクリプト）とログ出力の標準化
4. 基本的なユニットテストと疑似データを用いた保存処理の検証

## 技術スタック候補
- 言語: Python 3.11+
- パッケージ管理: `uv`
- 主要ライブラリ:
  - `alpaca-py`（ヒストリカルデータ取得）citeturn1search1
  - `pandas`（データ整形）
  - `sqlalchemy` + `asyncpg`（非同期DBアクセス）
  - `pydantic-settings`（設定管理）
  - `tenacity`（リトライ制御、必要に応じて）
- DB: PostgreSQL（dockerコンテナを前提）
- テスト: `pytest`, `pyfakefs`（必要時）, `responses`（HTTPスタブ）, `pytest-asyncio`

## アーキテクチャ概要
### コンポーネント
- `config/settings.py`  
  環境変数/APIキー/データ取得パラメータ（シンボル、期間、タイムフレーム、保存先テーブルなど）を集中管理。
- `clients/alpaca.py`  
  Alpaca SDKクライアント生成（Stock/Crypto/Option `HistoricalDataClient`、`NewsClient`）。APIキーは環境変数から注入。citeturn1search1
- `fetchers/`  
  各資産クラス別に`fetch_***`関数を提供。AlpacaのRequestオブジェクトを受け取り、DataFrameへ変換。
- `repository/postgres.py`  
  SQLAlchemy Coreを介したバルクUpsert処理とスナップショット管理。共通でタイムスタンプ・ソース情報を保持。テーブルはPostgreSQLの`alpaca`スキーマに集約する。
- `services/historical.py`  
  フロー制御を担うサービス層。フェッチ→検証→保存→ログまでを一連で実行し、後続のAPI層・スケジューラから呼び出せる形に整える。
- `tasks/`  
  CLI/スケジューラ用タスク定義（例: `python -m tasks.fetch --kind stock --symbols AAPL,MSFT`）。将来的なCeleryやAPScheduler統合を想定。

### データフロー
1. 設定読み込み：取得対象や期間を環境変数・設定ファイルから読み込む。
2. クライアント生成：`clients/alpaca.py`で各種クライアントを初期化（crypto/newsはAPIキー省略可）。citeturn1search1
3. フェッチ：`fetch_***`関数でRequestを構築し、bars/trades/quotes等の必要データを取得。
4. 整形：共通スキーマに合わせてカラム名統一、タイムゾーン処理、重複排除、メタ情報（取得日時・リクエストID）付与。
5. 保存：PostgreSQLへUpsertし履歴を蓄積。保存結果をログに記録。
6. 成功/失敗ログ・メトリクス送信：構築予定の監視基盤（例: Datadog）へメトリクス送信するインタフェースを残す。

## スキーマ設計（案）
| テーブル           | 主キー                               | 主なカラム                                                                              | 備考                                                               |
| ------------------ | ------------------------------------ | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `stock_bars`       | (`symbol`, `timestamp`, `timeframe`) | `open`, `high`, `low`, `close`, `volume`, `trade_count`, `vw`                           | bars基準。timeframeは`alpaca.data.timeframe.TimeFrame`を文字列化。 |
| `crypto_bars`      | (`symbol`, `timestamp`, `timeframe`) | `open`, `high`, `low`, `close`, `volume`, `trade_count`, `vw`                           | Crypto固有で`exchange`や`isotimestamp`を保持。                     |
| `option_bars`      | (`symbol`, `timestamp`, `timeframe`) | `open`, `high`, `low`, `close`, `volume`, `open_interest`, `underlying_symbol`          | オプションは契約情報を別テーブル`option_contracts`で正規化予定。   |
| `news_articles`    | (`id`)                               | `headline`, `summary`, `url`, `author`, `symbols`, `created_at`, `updated_at`, `source` | Alpaca News APIのレスポンスIDを主キー化。                          |
| `option_contracts` | (`symbol`)                           | `expiration`, `strike`, `type`, `multiplier`, `root_symbol`                             | オプション仕様情報を格納。                                         |

※初期リリースではbars中心に保存し、trades/quotesは必要に応じてテーブルを拡張する。

## エラーハンドリングとリトライ方針
- ネットワークエラー・429レート制限時は指数バックオフでリトライ（最大3回）。
- APIレスポンス構造変更に備え、デシリアライザで厳密なスキーマ検証を実施（`pydantic`モデル利用）。
- 保存時のDB接続エラーはトランザクション単位でロールバックし、メトリクスへアラート通知。

## テスト戦略
- `tests/fetchers/test_stock.py`等でAlpaca SDKのレスポンスをスタブ化し、DataFrame整形結果を検証。
- `tests/repository/test_postgres.py`で`pytest-asyncio`+`docker-compose`を用いて実DBへ書き込み検証。
- テストケースにはDocstring形式でテストの目的・観点（正常系・境界日付・欠損値処理など）を日本語で明記する。
- Lint/Typeチェック：`ruff check`, `pyright`, `pytest`をCIへ組み込み。

## ロギングと監視
- `structlog`でJSON形式ログ出力。各タスク実行時間、取得件数、保存件数、警告を記録。
- 将来的なDatadog連携のため、メトリクスメタデータ（シンボル数、失敗回数）をエクスポートできる構造を設計。

## 今後のAPI化に向けた展望
- `services/historical.py`の各フローをFastAPIエンドポイント（POST `/tasks/historical/{asset_kind}`）から呼び出せるようにする。
- 認証付きで非同期タスクキュー（例: Celery/RQ）へジョブ投入し、結果をジョブIDで参照可能にする。
- フロント層からシンボルリストや期間を指定して実行できるよう、DBにジョブ履歴テーブルを追加。

## リスクとオープン課題
- オプションデータの可用範囲が直近データに限定されているため、長期遡及レポートは制約がある。citeturn1search0
- 大量シンボル取得時のAPI制限（200リクエスト/分）を超えないようバッチ制御が必要。citeturn1search7
- ニュースデータのレスポンス量が大きいため、保存前に不要フィールド整理とバッチサイズ調整を行う。
