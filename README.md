# AI営業自動化ツール for 運送会社

有限会社翔栄サービス向けに、見込み客の収集、営業優先度の判定、問い合わせ文面の生成、活動履歴の管理を行うStreamlitアプリです。

## セットアップ

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

`.env` に必要に応じてAPIキーや自社情報を設定してください。

- `SERPER_API_KEY`: 会社検索APIとしてSerperを使う場合
- `OPENAI_API_KEY`: AI提案文生成にOpenAIを使う場合
- `DATABASE_URL`: Supabase PostgreSQLを使う場合
- `APP_PASSWORD`: 公開URLにアクセスするためのパスワード

デフォルト自社情報は、有限会社翔栄サービスの会社案内をもとに設定しています。

- 会社名: 有限会社翔栄サービス
- 代表者: 原田 裕士
- 本社営業所: 〒370-1104 群馬県佐波郡玉村町上福島752
- 電話: 0270-64-2429
- 事業内容: 緊急配送、チャーター便、定期便、スポット便、軽貨物、ハンドキャリー、引越し・移転など

`DATABASE_URL` が未設定の場合はローカルSQLite、設定済みの場合はSupabase/PostgreSQLへ保存します。

## Supabase DB化

SupabaseのSQL Editorで [supabase_schema.sql](supabase_schema.sql) を実行してください。

その後、`.env` または Streamlit Cloud Secrets に接続文字列を設定します。

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres
```

Streamlit Cloudでは `.env` は使わず、Secrets に以下の形式で登録します。

```toml
DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres"
SERPER_API_KEY = "..."
OPENAI_API_KEY = "..."
APP_PASSWORD = "client-access-password"
```

既存のローカルSQLiteデータをSupabaseへ移す場合:

```powershell
$env:DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_REF.supabase.co:5432/postgres"
python scripts/migrate_sqlite_to_supabase.py
```

## クライアント向け公開

無料で公開する場合は Streamlit Community Cloud を使います。

1. GitHubにこのフォルダをリポジトリとしてアップロード
2. Streamlit Community Cloudで **Create app**
3. Repository、Branch、Main file path に `main.py` を指定
4. Advanced settings の Secrets に `.streamlit/secrets.toml.example` を参考に設定
5. Deploy
6. 発行された `https://...streamlit.app` のURLと `APP_PASSWORD` をクライアントに共有

`.env`、`.streamlit/secrets.toml`、`sales_ai.sqlite3` はGitHubに上げないでください。

## 起動

```powershell
python -m streamlit run main.py
```

このプロジェクトでは `.streamlit/config.toml` でポートを `18731` に固定しています。

ブラウザで開くURL:

```text
http://localhost:18731
```

## MVPでできること

- 業種・エリアを指定した見込み客検索
- SQLiteまたはSupabase/PostgreSQLへの企業保存
- 運送ニーズのスコアリング
- AIまたはテンプレートによる提案文生成
- 問い合わせフォームURLと入力項目の検出
- ステータス、活動履歴の管理

## 運用上の注意

大量自動送信は行わず、送信前に人間が確認する運用を前提にしています。reCAPTCHAの回避や同一企業への反復送信は避けてください。
