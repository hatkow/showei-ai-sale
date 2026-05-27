from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def get_setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return default


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = get_setting("OPENAI_API_KEY")
    serper_api_key: str | None = get_setting("SERPER_API_KEY")
    database_url: str | None = get_setting("DATABASE_URL")
    app_password: str | None = get_setting("APP_PASSWORD", "Showei2429")
    sales_company_name: str = get_setting("SALES_COMPANY_NAME", "有限会社翔栄サービス") or ""
    sales_contact_name: str = get_setting("SALES_CONTACT_NAME", "原田 裕士") or ""
    sales_email: str = get_setting("SALES_EMAIL", "info@example.com") or ""
    sales_phone: str = get_setting("SALES_PHONE", "0270-64-2429") or ""
    sales_area: str = get_setting("SALES_AREA", "群馬県・関東エリア・全国対応") or ""
    sales_address: str = get_setting("SALES_ADDRESS", "〒370-1104 群馬県佐波郡玉村町上福島752") or ""
    sales_profile: str = get_setting(
        "SALES_PROFILE",
        (
            "群馬県を拠点に、緊急配送、チャーター便、定期便、スポット便、"
            "軽貨物、ハンドキャリー、引越し・移転などを行う運送会社です。"
            "小荷物から大荷物まで対応し、ウィング、平ボディ、パワーゲート、"
            "幌などの車両でお客様のニーズに応えます。"
        ),
    )
    database_path: str = get_setting("DATABASE_PATH", "sales_ai.sqlite3") or "sales_ai.sqlite3"


settings = Settings()
