from __future__ import annotations

import requests
from urllib.parse import urlparse

from config import settings
from lead_analyzer import analyze_company


EXCLUDED_DOMAINS = {
    "bmb.jp",
    "tayori.com",
    "global-axis.jp",
    "blastmail.jp",
    "mailwise.cybozu.co.jp",
}

EXCLUDED_TITLE_WORDS = (
    "書き方",
    "例文",
    "テンプレート",
    "マナー",
    "ポイント",
    "徹底解説",
    "とは",
)


def search_companies(keyword: str, area: str, num: int = 20) -> list[dict]:
    if settings.serper_api_key:
        return _search_with_serper(keyword, area, num)
    return []


def _search_with_serper(keyword: str, area: str, num: int) -> list[dict]:
    companies = _search_places_with_serper(keyword, area, num)
    if companies:
        return companies
    return _search_organic_with_serper(keyword, area, num)


def _search_places_with_serper(keyword: str, area: str, num: int) -> list[dict]:
    query = f"{area} {keyword}"
    response = requests.post(
        "https://google.serper.dev/places",
        headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
        json={"q": query, "num": min(max(num, 10), 50), "gl": "jp", "hl": "ja"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    companies = []
    for item in payload.get("places", []):
        if len(companies) >= num:
            break
        name = item.get("title", "").strip()
        url = item.get("website")
        if not name or not url or _is_excluded_result(name, item.get("category", ""), url):
            continue
        company = {
            "name": name,
            "url": url,
            "industry": item.get("category") or keyword,
            "area": area,
            "address": item.get("address"),
            "phone": item.get("phoneNumber"),
            "summary": _place_summary(item),
            "status": "未確認",
        }
        companies.append(analyze_company(company))
    return companies


def _search_organic_with_serper(keyword: str, area: str, num: int) -> list[dict]:
    query = f"{area} {keyword} 会社 企業 -書き方 -例文 -テンプレート -マナー"
    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
        json={"q": query, "num": min(max(num * 3, 10), 50), "gl": "jp", "hl": "ja"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()

    companies = []
    for item in payload.get("organic", []):
        if len(companies) >= num:
            break
        name = item.get("title", "").split("|")[0].split("｜")[0].strip()
        url = item.get("link")
        if not name or not url or _is_excluded_result(name, item.get("snippet", ""), url):
            continue
        company = {
            "name": name,
            "url": url,
            "industry": keyword,
            "area": area,
            "summary": item.get("snippet"),
            "status": "未確認",
        }
        companies.append(analyze_company(company))
    return companies


def _place_summary(item: dict) -> str:
    parts = []
    for key in ("category", "address", "phoneNumber"):
        if item.get(key):
            parts.append(str(item[key]))
    if item.get("rating"):
        parts.append(f"Google評価 {item['rating']}")
    return " / ".join(parts)


def _is_excluded_result(title: str, snippet: str | None, url: str) -> bool:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")
    text = f"{title} {snippet or ''}".lower()
    if domain in EXCLUDED_DOMAINS:
        return True
    if any(word.lower() in text for word in EXCLUDED_TITLE_WORDS):
        return True
    if parsed.path.lower().endswith((".pdf", ".jpg", ".png")):
        return True
    return False


def _sample_companies(keyword: str, area: str, num: int) -> list[dict]:
    seeds = [
        ("関東フレッシュ食品株式会社", "食品製造", "冷凍食品と惣菜の製造、首都圏スーパーへの定期納品を展開"),
        ("東都EC物流サポート株式会社", "EC・通販", "通販商品の保管、梱包、出荷代行、倉庫間輸送を実施"),
        ("彩北メディカル用品株式会社", "医療・介護用品卸", "介護施設向け消耗品を関東一円へ定期配送"),
        ("千葉ベーカリー卸株式会社", "食品卸", "ベーカリー資材と冷蔵商品の店舗納品を手掛ける"),
        ("横浜建材プロダクト株式会社", "建材製造", "建材部品の工場間輸送と現場納品が多い"),
    ]
    results = []
    for index, (name, industry, summary) in enumerate(seeds[:num], start=1):
        company = {
            "name": name,
            "url": f"https://example.com/sample-{index}",
            "industry": industry or keyword,
            "area": area,
            "summary": summary,
            "contact_url": f"https://example.com/sample-{index}/contact",
            "status": "未確認",
        }
        results.append(analyze_company(company))
    return results
