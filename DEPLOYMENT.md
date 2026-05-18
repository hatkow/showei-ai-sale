# デプロイ手順

## 1. Supabase

SupabaseのSQL Editorで `supabase_schema.sql` を実行します。

実行後、以下のテーブルができていればOKです。

- `companies`
- `forms`
- `proposals`
- `activities`
- `send_logs`

## 2. ローカル接続確認

`.env` に以下を設定します。

```env
DATABASE_URL=postgresql://...
SERPER_API_KEY=...
OPENAI_API_KEY=...
APP_PASSWORD=...
```

確認コマンド:

```powershell
python scripts/deploy_check.py
```

`DB connection: OK` と `DB mode: PostgreSQL/Supabase` が出ればOKです。

## 3. GitHub

`.env`、`.streamlit/secrets.toml`、`sales_ai.sqlite3` はアップロードしないでください。

```powershell
git init
git add .
git status
git commit -m "Prepare Streamlit Supabase deployment"
```

その後、GitHubで空のリポジトリを作り、表示された手順に従ってpushします。

## 4. Streamlit Community Cloud

1. Streamlit Community Cloudで **Create app**
2. GitHubリポジトリを選択
3. Main file path に `main.py`
4. Advanced settings の Secrets に以下を設定

```toml
DATABASE_URL = "postgresql://..."
SERPER_API_KEY = "..."
OPENAI_API_KEY = "..."
APP_PASSWORD = "client-access-password"
```

5. Deploy

発行された `https://...streamlit.app` と `APP_PASSWORD` をクライアントへ共有します。

## 5. ローカル起動

```powershell
.\scripts\start_local.ps1
```

URL:

```text
http://localhost:18731
```
