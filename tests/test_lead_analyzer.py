from lead_analyzer import analyze_company


def test_analyze_company_scores_high_for_food_delivery_need():
    company = {
        "name": "関東食品株式会社",
        "industry": "食品製造",
        "area": "埼玉県",
        "summary": "スーパーへの定期納品と店舗配送を行う",
        "url": "https://example.com",
        "contact_url": "https://example.com/contact",
    }

    result = analyze_company(company)

    assert result["need_score"] >= 80
    assert "定期" in result["score_reason"] or "食品" in result["score_reason"]
    assert "定期便" in result["suggested_offer"]


def test_analyze_company_keeps_score_in_range():
    result = analyze_company({"name": "株式会社サンプル"})

    assert 0 <= result["need_score"] <= 100
