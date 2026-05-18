from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import settings
from db import IS_POSTGRES, init_db, list_companies, list_send_logs


def masked(value: str | None) -> str:
    if not value:
        return "未設定"
    if len(value) <= 8:
        return "設定済み"
    return f"設定済み ({value[:4]}...{value[-4:]})"


def main() -> None:
    print("Deployment check")
    print("================")
    print(f"DATABASE_URL: {masked(settings.database_url)}")
    print(f"SERPER_API_KEY: {masked(settings.serper_api_key)}")
    print(f"OPENAI_API_KEY: {masked(settings.openai_api_key)}")
    print(f"APP_PASSWORD: {'設定済み' if settings.app_password else '未設定'}")
    print(f"DB mode: {'PostgreSQL/Supabase' if IS_POSTGRES else 'SQLite local'}")

    init_db()
    print("DB connection: OK")
    print(f"companies: {len(list_companies())}")
    print(f"send_logs: {len(list_send_logs())}")


if __name__ == "__main__":
    main()
