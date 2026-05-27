from __future__ import annotations

import json

from openai import OpenAI

from config import settings


def generate_proposal(company: dict) -> tuple[str, str]:
    if settings.openai_api_key:
        return _generate_with_openai(company)
    return _generate_template(company)


def generate_resend_proposal(
    company: dict,
    previous_subject: str,
    previous_message: str,
    approach: str,
) -> tuple[str, str]:
    if settings.openai_api_key:
        return _generate_resend_with_openai(company, previous_subject, previous_message, approach)
    return _generate_resend_template(company, approach)


def generate_fax_proposal(company: dict) -> tuple[str, str]:
    if settings.openai_api_key:
        return _generate_fax_with_openai(company)
    return _generate_fax_template(company)


def _generate_with_openai(company: dict) -> tuple[str, str]:
    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f"""
あなたは中小運送会社の営業担当です。問い合わせフォームに入力する自然で丁寧な営業文を日本語で作成してください。

営業会社:
- 会社名: {settings.sales_company_name}
- 担当者: {settings.sales_contact_name}
- 対応エリア: {settings.sales_area}
- 所在地: {settings.sales_address}
- 会社概要: {settings.sales_profile}

対象企業:
- 会社名: {company.get("name")}
- 業種: {company.get("industry")}
- エリア: {company.get("area")}
- 事業概要: {company.get("summary")}
- 提案候補: {company.get("suggested_offer")}

条件:
- 売り込みすぎない
- 気遣い、時間厳守、緊急配送、チャーター便、定期便・ルート便の強みを自然に含める
- 2024年問題、欠車リスク、配送コスト安定も必要に応じて自然に含める
- 300〜450字程度
- 件名と本文を分ける
- JSONで subject と message のみ返す
"""
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        text={"format": {"type": "json_object"}},
    )
    data = json.loads(response.output_text)
    return data["subject"], data["message"]


def _generate_resend_with_openai(
    company: dict,
    previous_subject: str,
    previous_message: str,
    approach: str,
) -> tuple[str, str]:
    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f"""
あなたは中小運送会社の営業担当です。過去に送った営業文とは切り口を変えて、再送用の問い合わせ文を作成してください。

営業会社:
- 会社名: {settings.sales_company_name}
- 担当者: {settings.sales_contact_name}
- 対応エリア: {settings.sales_area}
- 会社概要: {settings.sales_profile}

対象企業:
- 会社名: {company.get("name")}
- 業種: {company.get("industry")}
- エリア: {company.get("area")}
- 事業概要: {company.get("summary")}
- 提案候補: {company.get("suggested_offer")}

前回送信:
- 件名: {previous_subject}
- 本文: {previous_message}

今回の別アプローチ:
{approach}

条件:
- 前回と同じ表現を避ける
- 追い営業感を弱め、情報提供・相談ベースにする
- 300〜450字程度
- 件名と本文を分ける
- JSONで subject と message のみ返す
"""
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        text={"format": {"type": "json_object"}},
    )
    data = json.loads(response.output_text)
    return data["subject"], data["message"]


def _generate_fax_with_openai(company: dict) -> tuple[str, str]:
    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f"""
運送会社から法人宛に送るFAX営業文を日本語で作成してください。

営業会社:
- 会社名: {settings.sales_company_name}
- 担当者: {settings.sales_contact_name}
- 電話: {settings.sales_phone}
- メール: {settings.sales_email}
- 対応エリア: {settings.sales_area}
- 会社概要: {settings.sales_profile}

対象企業:
- 会社名: {company.get("name")}
- 業種: {company.get("industry")}
- 住所/エリア: {company.get("address") or company.get("area")}
- 提案候補: {company.get("suggested_offer")}

条件:
- FAXで読みやすいように短く、見出し付き
- 売り込みすぎず、配送体制の相談・情報交換として書く
- 緊急配送、チャーター便、定期便、スポット便の対応力を自然に入れる
- 2024年問題、欠車リスク、配送コスト安定を必要に応じて入れる
- 件名と本文を分ける
- JSONで subject と message のみ返す
"""
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
        text={"format": {"type": "json_object"}},
    )
    data = json.loads(response.output_text)
    return data["subject"], data["message"]


def _generate_template(company: dict) -> tuple[str, str]:
    company_name = company.get("name") or "ご担当者様"
    industry = company.get("industry") or "貴社事業"
    offer = company.get("suggested_offer") or "定期便・ルート便"
    subject = f"配送体制に関するご相談（{settings.sales_company_name}）"
    message = f"""突然のご連絡失礼いたします。{settings.sales_company_name}の{settings.sales_contact_name}と申します。

弊社は{settings.sales_area}を中心に、定期便・ルート便・スポット配送のご相談を承っております。貴社の{industry}に関する事業内容を拝見し、{offer}の面でお役に立てる可能性があるのではないかと思い、ご連絡いたしました。

弊社は群馬県を拠点に、緊急配送、チャーター便、定期便、スポット便、軽貨物などに対応しており、小荷物から大荷物まで、お客様のご事情に合わせた配送体制をご提案しています。2024年問題以降、配送コストの安定や欠車リスクへの備えについてご相談をいただく機会も増えております。

現在の配送体制でお困りごとや、今後の委託先見直しの予定がございましたら、一度情報交換のお時間をいただけますと幸いです。

何卒よろしくお願いいたします。

{settings.sales_company_name}
{settings.sales_contact_name}
{settings.sales_email}
{settings.sales_phone}"""
    return subject, message


def _generate_resend_template(company: dict, approach: str) -> tuple[str, str]:
    industry = company.get("industry") or "貴社事業"
    offer = company.get("suggested_offer") or "定期便・ルート便"
    subject = f"配送体制の見直しに関する情報交換のお願い（{settings.sales_company_name}）"
    message = f"""以前、配送体制に関するご相談でご連絡いたしました、{settings.sales_company_name}の{settings.sales_contact_name}です。

今回は少し切り口を変え、{approach}の観点でご連絡いたしました。貴社の{industry}に関する事業では、繁忙期や急な物量変動、定期納品の安定化など、配送面で事前に備えておく価値がある場面もあるかと存じます。

弊社では、群馬県を拠点に緊急配送、チャーター便、定期便、スポット便、軽貨物などに対応しており、{offer}についてもご相談いただけます。すぐのご依頼でなくても、今後の選択肢の一つとして一度情報交換できましたら幸いです。

何卒よろしくお願いいたします。

{settings.sales_company_name}
{settings.sales_contact_name}
{settings.sales_email}
{settings.sales_phone}"""
    return subject, message


def _generate_fax_template(company: dict) -> tuple[str, str]:
    company_name = company.get("name") or "ご担当者様"
    offer = company.get("suggested_offer") or "定期便・チャーター便"
    subject = f"配送体制に関するご相談（{settings.sales_company_name}）"
    message = f"""FAX送付のご案内

{company_name}
物流・配送ご担当者様

突然のご連絡失礼いたします。
{settings.sales_company_name}の{settings.sales_contact_name}と申します。

弊社は{settings.sales_area}を中心に、緊急配送、チャーター便、定期便、スポット便、軽貨物配送などを行っております。

貴社の配送体制において、{offer}、急な物量増加、欠車リスク対策、配送コストの安定化などでお困りごとがございましたら、一度情報交換の機会をいただけますと幸いです。

すぐのご依頼でなくても、今後の委託先候補としてご相談いただける体制を整えております。

何卒よろしくお願いいたします。

{settings.sales_company_name}
担当: {settings.sales_contact_name}
TEL: {settings.sales_phone}
MAIL: {settings.sales_email}"""
    return subject, message
