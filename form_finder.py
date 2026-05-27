from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


CONTACT_KEYWORDS = ("お問い合わせ", "問合せ", "contact", "inquiry", "見積", "相談")
CONTACT_FIELD_HINTS = (
    "name",
    "email",
    "mail",
    "tel",
    "phone",
    "message",
    "body",
    "company",
    "subject",
    "your-",
    "お名前",
    "メール",
    "電話",
    "会社",
    "件名",
    "内容",
    "相談",
    "問い合わせ",
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:0\d{1,4}[-\s]?\d{1,4}[-\s]?\d{3,4})")
LABELED_PHONE_RE = re.compile(
    r"(?:TEL|Tel|tel|電話|電話番号)[：:．.\s]*"
    r"(0\d{1,4}[-－ー\s]?\d{1,4}[-－ー\s]?\d{3,4})"
)
HYPHEN_PHONE_RE = re.compile(r"(0\d{1,4}[-－ー]\d{1,4}[-－ー]\d{3,4})")
FAX_RE = re.compile(
    r"(?:ＦＡＸ番号|FAX番号|FAX|Fax|fax|ＦＡＸ|ファックス)[：:．.\s]*"
    r"([0-9０-９]{2,5}[-－ー\s]?[0-9０-９]{1,4}[-－ー\s]?[0-9０-９]{3,4})"
)


def find_contact_form(url: str) -> dict:
    visited: set[str] = set()
    candidates: list[str] = [url]

    try:
        response = _fetch(url)
    except requests.RequestException as exc:
        return {
            "form_url": url,
            "fields": [],
            "has_captcha": False,
            "can_autofill": False,
            "notes": f"ページ取得に失敗しました: {exc}",
        }

    soup = BeautifulSoup(response.text, "html.parser")
    base_text = soup.get_text(" ", strip=True)
    base_emails = _extract_emails(response.text)
    base_phones = _extract_phones(base_text)
    base_faxes = _extract_faxes(base_text)
    candidates.extend(_common_contact_urls(url))
    candidates.extend(_find_contact_links(url, soup))

    for candidate in _dedupe(candidates):
        if candidate in visited or not _same_site(url, candidate):
            continue
        visited.add(candidate)
        try:
            candidate_response = response if candidate == url else _fetch(candidate)
        except requests.RequestException:
            continue
        candidate_soup = BeautifulSoup(candidate_response.text, "html.parser")
        fields = _extract_contact_fields(candidate_soup)
        page_text = candidate_soup.get_text(" ", strip=True)
        has_captcha = _has_captcha(candidate_response.text, page_text)
        emails = _extract_emails(candidate_response.text)
        phones = _extract_phones(page_text)
        faxes = _extract_faxes(page_text)
        merged_emails = _dedupe_values([*emails, *base_emails])
        merged_phones = _dedupe_values([*phones, *base_phones])
        merged_faxes = _dedupe_values([*faxes, *base_faxes])

        if fields:
            return {
                "form_url": candidate,
                "fields": fields,
                "emails": merged_emails,
                "phones": merged_phones,
                "faxes": merged_faxes,
                "has_captcha": has_captcha,
                "can_autofill": not has_captcha,
                "notes": _notes("問い合わせフォームを検出しました", merged_emails, merged_phones, merged_faxes),
            }

    emails = _extract_emails(response.text)
    page_text = soup.get_text(" ", strip=True)
    phones = _extract_phones(page_text)
    faxes = _extract_faxes(page_text)
    return {
        "form_url": candidates[0],
        "fields": [],
        "emails": emails,
        "phones": phones,
        "faxes": faxes,
        "has_captcha": _has_captcha(response.text, soup.get_text(" ", strip=True)),
        "can_autofill": False,
        "notes": _notes("問い合わせフォームは見つかりませんでした", emails, phones, faxes),
    }


def _fetch(url: str) -> requests.Response:
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "SalesResearchBot/0.1 (+contact form discovery)"},
    )
    response.raise_for_status()
    return response


def _find_contact_links(base_url: str, soup: BeautifulSoup) -> list[str]:
    scored_links: list[tuple[int, str]] = []
    for link in soup.find_all("a", href=True):
        text = link.get_text(" ", strip=True).lower()
        href_raw = link["href"]
        if href_raw.startswith(("mailto:", "tel:", "#")):
            continue
        href = urljoin(base_url, href_raw)
        haystack = f"{text} {href_raw}".lower()
        score = 0
        if "contact" in haystack or "お問合せ" in haystack or "お問い合わせ" in haystack:
            score += 100
        if "問合せ" in haystack or "inquiry" in haystack:
            score += 90
        if "見積" in haystack or "quote" in haystack or "estimate" in haystack:
            score += 70
        if "相談" in haystack:
            score += 50
        if "法人" in haystack or "企業" in haystack:
            score += 20
        if "recruit" in haystack or "採用" in haystack or "求人" in haystack or "entry" in haystack:
            score -= 160
        if "private" in haystack or "個人" in haystack or "引越" in haystack or "moving" in haystack:
            score -= 35
        if score > 0:
            scored_links.append((score, href))
    scored_links.sort(key=lambda item: item[0], reverse=True)
    return [href for _, href in scored_links]


def _common_contact_urls(base_url: str) -> list[str]:
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    return [
        urljoin(root, path)
        for path in (
            "/contact/",
            "/inquiry/",
            "/contact-us/",
            "/otoiawase/",
            "/toiawase/",
            "/estimate/",
            "/quote/",
        )
    ]


def _extract_contact_fields(soup: BeautifulSoup) -> list[dict]:
    best_fields: list[dict] = []
    for form in soup.find_all("form"):
        fields = []
        for element in form.find_all(["input", "textarea", "select"]):
            field_type = element.get("type") or element.name
            if field_type in ("hidden", "submit", "button"):
                continue
            fields.append(
                {
                    "tag": element.name,
                    "name": element.get("name") or "",
                    "id": element.get("id") or "",
                    "type": field_type,
                    "label": _label_for(soup, element),
                    "required": element.has_attr("required") or "必須" in _label_for(soup, element),
                }
            )
        if _is_contact_form(fields) and len(fields) > len(best_fields):
            best_fields = fields
    return best_fields


def _is_contact_form(fields: list[dict]) -> bool:
    if not fields:
        return False
    haystack = " ".join(
        f"{field.get('name', '')} {field.get('id', '')} {field.get('type', '')} {field.get('label', '')}"
        for field in fields
    ).lower()
    has_message = any(field["tag"] == "textarea" for field in fields)
    has_contact_channel = any(field.get("type") in ("email", "tel") for field in fields)
    has_hint = any(hint.lower() in haystack for hint in CONTACT_FIELD_HINTS)
    is_search_only = len(fields) == 1 and (
        fields[0].get("name") == "s"
        or fields[0].get("type") == "search"
        or "検索" in fields[0].get("label", "")
    )
    return not is_search_only and (has_message or has_contact_channel or has_hint)


def _has_captcha(html: str, page_text: str) -> bool:
    text = f"{html} {page_text}".lower()
    return "recaptcha" in text or "captcha" in text


def _extract_emails(html: str) -> list[str]:
    return sorted({email for email in EMAIL_RE.findall(html) if not email.endswith((".png", ".jpg"))})


def _extract_phones(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).replace("ー", "-").replace("－", "-")
    values = [*_normalize_numbers(LABELED_PHONE_RE.findall(normalized)), *_normalize_numbers(HYPHEN_PHONE_RE.findall(normalized))]
    return _dedupe_values(values)


def _extract_faxes(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).replace("ー", "-").replace("－", "-")
    return _dedupe_values([match.strip().replace(" ", "-") for match in FAX_RE.findall(normalized)])


def _notes(base: str, emails: list[str], phones: list[str], faxes: list[str]) -> str:
    parts = [base]
    real_emails = [email for email in emails if "example." not in email.lower()]
    if real_emails:
        parts.append(f"メール候補: {', '.join(real_emails[:3])}")
    if phones:
        parts.append(f"電話候補: {', '.join(phones[:3])}")
    if faxes:
        parts.append(f"FAX候補: {', '.join(faxes[:3])}")
    return " / ".join(parts)


def _same_site(original_url: str, candidate_url: str) -> bool:
    return urlparse(original_url).netloc == urlparse(candidate_url).netloc


def _dedupe(urls: list[str]) -> list[str]:
    seen = set()
    results = []
    for url in urls:
        normalized = url.split("#")[0]
        if normalized not in seen:
            seen.add(normalized)
            results.append(normalized)
    return results


def _dedupe_values(values: list[str]) -> list[str]:
    seen = set()
    results = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            results.append(value)
    return results


def _normalize_numbers(values: list[str]) -> list[str]:
    return ["-".join(value.split()) for value in values]


def _label_for(soup: BeautifulSoup, element) -> str:
    element_id = element.get("id")
    if element_id:
        label = soup.find("label", attrs={"for": element_id})
        if label:
            return label.get_text(" ", strip=True)
    parent_label = element.find_parent("label")
    if parent_label:
        return parent_label.get_text(" ", strip=True)
    return element.get("placeholder") or element.get("aria-label") or ""
