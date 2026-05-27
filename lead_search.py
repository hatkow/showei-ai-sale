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
    "itp.ne.jp",
    "its-mo.com",
    "ivry.jp",
    "job.mynavi.jp",
    "job.rikunabi.com",
    "mapion.co.jp",
    "blastmail.jp",
    "mailwise.cybozu.co.jp",
    "akitekt.net",
    "showei-service.com",
    "tayori.com",
    "wikipedia.org",
    "wiktionary.org",
    "x.com",
    "twitter.com",
    "prtimes.jp",
    "atpress.ne.jp",
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
    "アルバイト",
    "バイト",
    "求人ボックス",
    "indeed",
    "インディード",
    "スタンバイ",
    "タウンワーク",
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
            if not url and item.get("cid"):
                url = f"https://www.google.com/maps?cid={item['cid']}"
            if not name or not url or _is_excluded_result(name, item.get("category", ""), url):
                continue
            company = {
                "name": name,
                "url": url,
                "industry": item.get("category") or clean_keyword,
                "area": area,
                "address": item.get("address"),
                "phone": item.get("phoneNumber"),
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
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


def _find_company_website(name: str, area: str) -> str | None:
    query_name = _normalize_company_name(name)
    place_url = _find_company_website_from_places(name, area)
    if place_url:
        return place_url

    queries = [
        query_name,
        f"{query_name} ホームページ",
        f"{query_name} 公式サイト",
        f"{query_name} {area} 会社",
    ]
    candidates: list[tuple[int, int, str]] = []
    for query_order, query in enumerate(queries):
        candidates.extend(_search_company_website_candidates(query_name, query, query_order))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return candidates[0][2]


def _find_company_website_from_places(name: str, area: str) -> str | None:
    queries = [f"{name} {area}".strip(), name]
    for query in queries:
        try:
            response = requests.post(
                "https://google.serper.dev/places",
                headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
                json={"q": query, "num": 5, "gl": "jp", "hl": "ja"},
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException:
            continue
        for item in response.json().get("places", []):
            url = item.get("website")
            title = item.get("title", "")
            if url and not _is_excluded_result(title, item.get("category", ""), url):
                return url
    return None


def _search_company_website_candidates(company_name: str, query: str, query_order: int) -> list[tuple[int, int, str]]:
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
            json={
                "q": (
                    f"{query} -求人 -採用 -転職 -就活 -仕事 -Baseconnect "
                    "-doda -リクナビ -マイナビ -Wikipedia -Wiktionary"
                ),
                "num": 10,
                "gl": "jp",
                "hl": "ja",
            },
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException:
        return []

    candidates: list[tuple[int, int, str]] = []
    for item in response.json().get("organic", []):
        url = item.get("link")
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        if not url or _is_excluded_result(title, snippet, url):
            continue
        score = _official_site_score(company_name, title, snippet, url)
        if score > 0:
            candidates.append((score, query_order, url))
    return candidates


def find_company_website(name: str, area: str) -> str | None:
    if not settings.serper_api_key:
        return None
    return _find_company_website(name, area)


def find_google_map_listing(name: str, area: str) -> dict:
    if not settings.serper_api_key:
        return {}
    queries = [f"{name} {area}".strip(), name]
    for query in queries:
        try:
            response = requests.post(
                "https://google.serper.dev/places",
                headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"},
                json={"q": query, "num": 5, "gl": "jp", "hl": "ja"},
                timeout=20,
            )
            response.raise_for_status()
        except requests.RequestException:
            continue

        for item in response.json().get("places", []):
            title = item.get("title", "")
            website = item.get("website")
            if website and _is_excluded_result(title, item.get("category", ""), website):
                website = None
            if title or website:
                return {
                    "name": title,
                    "website": website,
                    "address": item.get("address"),
                    "phone": item.get("phoneNumber"),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "category": item.get("category"),
                    "cid": item.get("cid"),
                }
    return {}


def _normalize_company_name(name: str) -> str:
    normalized = (
        name.replace("（株）", "株式会社")
        .replace("(株)", "株式会社")
        .replace("㈱", "株式会社")
        .replace("　", " ")
    )
    for branch_word in ("太田支店", "本社工場", "支店", "営業所", "工場", "本社", "オフィス"):
        normalized = normalized.replace(branch_word, " ")
    return " ".join(normalized.split())


def _official_site_score(company_name: str, title: str, snippet: str, url: str) -> int:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")
    text = f"{title} {snippet}".lower()
    score = 0
    if ".co.jp" in domain or ".jp" in domain:
        score += 20
    if "公式" in title or "公式" in snippet:
        score += 30
    for token in company_name.replace("株式会社", " ").split():
        if token and token.lower() in text:
            score += 40
    if parsed.path in ("", "/"):
        score += 10
    if any(bad in text for bad in ("求人", "採用", "転職", "wiki", "辞書")):
        score -= 80
    return score


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
    if domain in {"google.com", "maps.google.com", "www.google.com"}:
        return False
    if any(word.lower() in text for word in EXCLUDED_TITLE_WORDS):
        return True
    if any(word in f"{title} {snippet or ''}" for word in ("求人", "仕事", "アルバイト", "バイト", "採用", "転職", "ドライバー")):
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
