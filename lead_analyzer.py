from __future__ import annotations

from urllib.parse import urlparse


HIGH_INTENT_WORDS = {
    "食品": 18,
    "ec": 18,
    "通販": 18,
    "卸": 14,
    "製造": 12,
    "工場": 12,
    "倉庫": 12,
    "納品": 16,
    "配送": 16,
    "物流": 14,
    "店舗": 10,
    "ルート": 12,
    "定期": 16,
    "医療": 10,
    "介護": 10,
    "建材": 9,
}


def analyze_company(company: dict) -> dict:
    text = " ".join(
        str(company.get(key, "") or "")
        for key in ("name", "industry", "area", "address", "summary", "url")
    ).lower()
    score = 35
    reasons: list[str] = []

    for word, weight in HIGH_INTENT_WORDS.items():
        if word.lower() in text:
            score += weight
            reasons.append(f"{word}関連の配送ニーズが想定される")

    if any(area in text for area in ("東京", "埼玉", "千葉", "神奈川", "茨城", "群馬", "栃木", "関東")):
        score += 12
        reasons.append("関東圏で提案対象エリアに合う")

    if company.get("contact_url") or "contact" in text or "inquiry" in text:
        score += 8
        reasons.append("問い合わせ導線があり営業接点を作りやすい")

    if urlparse(str(company.get("url", ""))).netloc:
        score += 5

    score = max(0, min(score, 100))
    if not reasons:
        reasons.append("公開情報からは一般的な法人配送ニーズとして評価")

    suggested_offer = _suggest_offer(text)
    return {
        **company,
        "need_score": score,
        "score_reason": "、".join(reasons[:3]),
        "suggested_offer": suggested_offer,
    }


def _suggest_offer(text: str) -> str:
    if any(word in text for word in ("食品", "店舗", "納品")):
        return "定期便・店舗納品・温度帯に応じた配送相談"
    if any(word in text for word in ("ec", "通販", "倉庫")):
        return "EC出荷補助・倉庫間輸送・スポットから定期化"
    if any(word in text for word in ("建材", "工場", "製造")):
        return "工場間輸送・現場納品・ルート便"
    return "定期便・ルート便・スポット便からの継続提案"
