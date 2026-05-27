from __future__ import annotations

import requests
from urllib.parse import urlparse

from config import settings
from lead_analyzer import analyze_company


EXCLUDED_DOMAINS = {
    "baseconnect.in",
    "bmb.jp",
    "buffett-code.com",
    "compalyze.co.jp",
    "doda.jp",
    "global-axis.jp",
    "ipros.com",
    "job.mynavi.jp",
    "job.rikunabi.com",
    "blastmail.jp",
    "mailwise.cybozu.co.jp",
    "showei-service.com",
    "tayori.com",
    "xn--pckua2a7gp15089zb.com",
}

EXCLUDED_TITLE_WORDS = (
    "baseconnect",
    "doda",
    "リクナビ",
    "マイナビ",
    "求人",
    "採用",
    "転職",
    "就活",
    "仕事",
    "ドライバー",
    "企業一覧",
    "企業情報",
    "採用データ",
    "書き方",
    "例文",
    "テンプレート",
    "マナー",
    "ポイント",
    "徹底解説",
    "とは",
)

INTENT_WORDS = (
    "定期配送",
    "定期便",
    "ルート配送",
    "ルート便",
    "配送",
    "運送",
    "求人",
    "採用",
    "仕事",
)


def search_companies(keyword: str, area: str, num: int = 20) -> list[dict]:
    if settings.serper_api_key:
        return _search_with_serper(keyword, area, num)
    return []


def _search_with_serper(keyword: str, area: str, num: int) -> list[dict]:
    return _search_places_with_serper(keyword, area, num)


def _search_places_with_serper(keyword: str, area: str, num: int) -> list[dict]:
    companies = []
    clean_keyword = _company_search_keyword(keyword)
    queries = _place_queries(clean_keyword, area)
    for query in queries:
        response = requests.post(
            "https://google.serper.dev/places",
            headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
            json={"q": query, "num": min(max(num, 10), 50), "gl": "jp", "hl": "ja"},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        for item in payload.get("places", []):
            if len(companies) >= num:
                return _dedupe_companies(companies)
            name = item.get("title", "").strip()
            url = item.get("website")
            if not name or not url or _is_excluded_result(name, item.get("category", ""), url):
                continue
            company = {
                "name": name,
                "url": url,
                "industry": item.get("category") or clean_keyword,
                "area": area,
                "address": item.get("address"),
                "phone": item.get("phoneNumber"),
                "summary": _place_summary(item),
                "status": "未確認",
            }
            companies.append(analyze_company(company))
        companies = _dedupe_companies(companies)
    return companies


def _search_organic_with_serper(keyword: str, area: str, num: int) -> list[dict]:
    clean_keyword = _company_search_keyword(keyword)
    query = (
        f"{area} {clean_keyword} 会社 企業 メーカー "
        "-求人 -採用 -転職 -就活 -仕事 -ドライバー -企業一覧 -企業情報 "
        "-Baseconnect -doda -リクナビ -マイナビ -Indeed"
    )
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
            "industry": clean_keyword,
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
    if domain in EXCLUDED_DOMAINS or any(domain.endswith(f".{excluded}") for excluded in EXCLUDED_DOMAINS):
        return True
    if any(word.lower() in text for word in EXCLUDED_TITLE_WORDS):
        return True
    if parsed.path.lower().endswith((".pdf", ".jpg", ".png")):
        return True
    return False


def _company_search_keyword(keyword: str) -> str:
    clean = keyword
    for word in INTENT_WORDS:
        clean = clean.replace(word, " ")
    return " ".join(clean.split()) or keyword


def _place_queries(clean_keyword: str, area: str) -> list[str]:
    if "建材" in clean_keyword:
        terms = [
            "建材店",
            "建設資材",
            "建築資材",
            "建材 販売",
            "建材 卸",
            "建材会社",
            "建材メーカー",
        ]
    elif "食品" in clean_keyword:
        terms = ["食品メーカー", "食品製造", "食品工場", "食品卸"]
    else:
        terms = [clean_keyword, f"{clean_keyword} 製造", f"{clean_keyword} 販売"]
    return [f"{area} {term}" for term in terms]


def _dedupe_companies(companies: list[dict]) -> list[dict]:
    seen = set()
    results = []
    for company in companies:
        key = (company.get("name"), urlparse(company.get("url") or "").netloc)
        if key in seen:
            continue
        seen.add(key)
        results.append(company)
    return results


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
