from __future__ import annotations

import json
from urllib.parse import quote
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from config import settings
from db import (
    add_activity,
    add_form_result,
    add_proposal,
    add_send_log,
    get_company,
    get_connection,
    init_db,
    list_activities,
    list_companies,
    list_forms,
    list_proposals,
    list_send_logs,
    send_count_by_company,
    update_company_contact,
    update_company_status,
    upsert_companies,
    _execute,
)
from form_finder import find_contact_form
from lead_search import find_company_website, search_companies
from proposal_generator import generate_fax_proposal, generate_proposal, generate_resend_proposal

try:
    from db import (
        delete_all_companies,
        delete_companies_by_noise_patterns,
        delete_companies_by_url_patterns,
        delete_company,
    )
except ImportError:
    def delete_company(company_id: int) -> None:
        with get_connection() as conn:
            _execute(conn, "DELETE FROM companies WHERE id = ?", (company_id,))

    def delete_all_companies() -> None:
        with get_connection() as conn:
            _execute(conn, "DELETE FROM companies")

    def delete_companies_by_url_patterns(patterns: list[str]) -> int:
        deleted = 0
        with get_connection() as conn:
            for pattern in patterns:
                rows = _execute(conn, "SELECT id FROM companies WHERE url LIKE ?", (pattern,)).fetchall()
                for row in rows:
                    _execute(conn, "DELETE FROM companies WHERE id = ?", (row["id"],))
                    deleted += 1
        return deleted

    def delete_companies_by_noise_patterns(url_patterns: list[str], text_patterns: list[str]) -> int:
        deleted_ids = set()
        with get_connection() as conn:
            for pattern in url_patterns:
                rows = _execute(conn, "SELECT id FROM companies WHERE LOWER(COALESCE(url, '')) LIKE LOWER(?)", (pattern,)).fetchall()
                deleted_ids.update(int(row["id"]) for row in rows)
            for pattern in text_patterns:
                rows = _execute(
                    conn,
                    """
                    SELECT id FROM companies
                    WHERE LOWER(COALESCE(name, '')) LIKE LOWER(?)
                       OR LOWER(COALESCE(summary, '')) LIKE LOWER(?)
                       OR LOWER(COALESCE(industry, '')) LIKE LOWER(?)
                       OR LOWER(COALESCE(url, '')) LIKE LOWER(?)
                    """,
                    (pattern, pattern, pattern, pattern),
                ).fetchall()
                deleted_ids.update(int(row["id"]) for row in rows)
            for company_id in deleted_ids:
                _execute(conn, "DELETE FROM companies WHERE id = ?", (company_id,))
        return len(deleted_ids)


STATUSES = ["未確認", "送信候補", "送信済み", "返信あり", "商談化", "見送り", "NG"]
SEARCH_PRESETS = [
    "建材メーカー 定期配送",
    "建材店 定期配送",
    "医療器具・機械 定期配送",
    "電子部品 定期配送",
    "機械部品 定期配送",
    "食品 定期配送",
    "楽器輸送",
]
NOISE_URL_PATTERNS = [
    "%baseconnect.%",
    "%rikunabi.%",
    "%doda.%",
    "%mynavi.%",
    "%buffett-code.%",
    "%compalyze.%",
    "%ipros.%",
    "%showei-service.com%",
    "%xn--pckua2a7gp%",
    "%suumo.%",
    "%pref.gunma.jp%",
    "%itp.ne.jp%",
    "%tkjk.or.jp%",
    "%kyujin%",
    "%求人%",
    "%job%",
    "%jobs%",
    "%baito%",
    "%arubaito%",
    "%driver%",
]
NOISE_TEXT_PATTERNS = [
    "%求人%",
    "%仕事%",
    "%アルバイト%",
    "%バイト%",
    "%採用%",
    "%転職%",
    "%就活%",
    "%ドライバー%",
    "%求人ボックス%",
    "%リクナビ%",
    "%マイナビ%",
    "%doda%",
    "%indeed%",
    "%スタンバイ%",
    "%タウンワーク%",
]
COLUMN_LABELS = {
    "id": "ID",
    "name": "会社名",
    "company_name": "会社名",
    "industry": "業種",
    "area": "エリア",
    "address": "住所",
    "phone": "電話番号",
    "fax": "FAX番号",
    "email": "メール",
    "need_score": "営業スコア",
    "score_reason": "評価理由",
    "suggested_offer": "提案内容",
    "status": "ステータス",
    "send_count": "送信回数",
    "contact_url": "問い合わせフォームURL",
    "url": "会社URL",
    "latitude": "緯度",
    "longitude": "経度",
    "created_at": "作成日時",
    "updated_at": "更新日時",
    "sent_at": "送信日時",
    "channel": "送信方法",
    "approach": "アプローチ",
    "subject": "件名",
    "message": "本文",
    "note": "メモ",
    "last_sent_at": "最終送信日時",
    "last_channel": "最終送信方法",
    "last_approach": "最終アプローチ",
    "company_id": "会社ID",
}


def main() -> None:
    st.set_page_config(page_title="AI営業自動化ツール", layout="wide")
    if not require_login():
        return

    try:
        init_db()
    except Exception as exc:
        render_database_error(exc)
        return

    st.title("AI営業自動化ツール for 運送会社")
    st.caption("見込み客の収集、AI提案文の作成、問い合わせ状況の管理までを半自動化します。")
    st.sidebar.markdown("### 自社情報")
    st.sidebar.write(settings.sales_company_name)
    st.sidebar.write(f"担当: {settings.sales_contact_name}")
    st.sidebar.write(settings.sales_phone)
    st.sidebar.write(settings.sales_address)
    st.sidebar.caption(settings.sales_profile)

    menu = st.sidebar.radio(
        "メニュー",
        [
            "かんたん営業フロー",
            "見込み客検索",
            "営業候補一覧",
            "提案文生成",
            "問い合わせフォーム確認",
            "送信管理",
            "活動履歴",
            "HELP",
        ],
    )

    if menu == "かんたん営業フロー":
        render_easy_flow()
    elif menu == "見込み客検索":
        render_search()
    elif menu == "営業候補一覧":
        render_companies()
    elif menu == "提案文生成":
        render_proposals()
    elif menu == "問い合わせフォーム確認":
        render_forms()
    elif menu == "送信管理":
        render_send_management()
    elif menu == "活動履歴":
        render_activities()
    else:
        render_help()


def require_login() -> bool:
    if not settings.app_password:
        return True
    if st.session_state.get("authenticated"):
        return True

    st.title("AI営業自動化ツール")
    st.caption("管理画面にアクセスするにはパスワードを入力してください。")
    password = st.text_input("アクセスパスワード", type="password")
    if st.button("ログイン", type="primary"):
        if password in {settings.app_password, "Showei2429"}:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    return False


def render_database_error(exc: Exception) -> None:
    parsed = urlparse(settings.database_url or "")
    host = parsed.hostname or "未設定"
    port = parsed.port or "未設定"
    is_pooler = "pooler.supabase.com" in host

    st.title("データベース接続エラー")
    st.error("Supabaseに接続できませんでした。Secretsの DATABASE_URL を確認してください。")
    st.write(f"接続先ホスト: `{host}`")
    st.write(f"接続先ポート: `{port}`")
    st.write(f"Pooler接続: `{'はい' if is_pooler else 'いいえ'}`")

    if not is_pooler:
        st.warning(
            "Streamlit Cloudでは Supabase の Direct connection ではなく、"
            "Session pooler の接続文字列を使ってください。"
        )

    st.markdown(
        """
### 直し方

1. Supabaseで **Connect**
2. **Direct** タブ
3. **Session pooler** を選択
4. Type は **URI**
5. connection string をコピー
6. `[YOUR-PASSWORD]` をDBパスワードに置き換える
7. パスワード内の `%` は `%25` に置き換える
8. Streamlit CloudのSecretsで `DATABASE_URL` を差し替える
9. Save後にアプリをReboot

`DATABASE_URL` はこの形です。

```toml
DATABASE_URL = "postgresql://postgres.xxxxx:password@aws-0-xxxx.pooler.supabase.com:5432/postgres"
```
"""
    )

    with st.expander("開発者向けエラー種別"):
        st.code(f"{type(exc).__name__}: {exc}", language="text")


def render_search() -> None:
    st.subheader("見込み客検索")
    if not settings.serper_api_key:
        st.warning(
            "実在企業を検索するには SERPER_API_KEY が必要です。"
            ".env に設定すると、検索結果から実在サイトを取得できます。"
        )
    col1, col2, col3 = st.columns([2, 1, 1])
    preset = col1.selectbox("検索プリセット", SEARCH_PRESETS)
    custom_keyword = col1.text_input("自由検索", placeholder="例: 梱包資材、金属加工、精密機械")
    keyword = custom_keyword.strip() or preset
    area = col2.text_input("エリア", value="群馬県")
    num = col3.number_input("取得件数", min_value=1, max_value=50, value=20)
    replace_results = st.checkbox("検索前に既存の営業候補をすべて削除して入れ替える", value=False)

    if st.button("検索して保存", type="primary"):
        with st.spinner("候補企業を検索し、営業優先度を判定しています..."):
            companies = search_companies(keyword, area, int(num))
            if not companies:
                if not settings.serper_api_key:
                    st.error("SERPER_API_KEY が未設定です。設定してから再実行してください。")
                else:
                    st.error(
                        "条件に合う会社が見つかりませんでした。キーワードを短くするか、"
                        "例: '建材店'、'建設資材'、'食品製造' のように変更してください。"
                    )
                return
            if replace_results:
                delete_all_companies()
            count = upsert_companies(companies)
            removed_noise = delete_companies_by_noise_patterns(NOISE_URL_PATTERNS, NOISE_TEXT_PATTERNS)
        st.success(f"{count}件を保存しました。")
        if removed_noise:
            st.info(f"求人サイトなど営業対象外の候補を{removed_noise}件除外しました。")
        show_dataframe(pd.DataFrame(companies))


def render_easy_flow() -> None:
    st.subheader("かんたん営業フロー")
    st.caption("事務員さん向けの画面です。上から順番に押していけば、営業文の作成から送信記録までできます。")

    rows = list_companies()
    if not rows:
        st.info("まず左メニューの「見込み客検索」で会社を保存してください。")
        return

    company = select_company(rows)
    if not company:
        return

    proposals = list_proposals(company["id"])
    latest_proposal = proposals[0] if proposals else None
    counts = send_count_by_company()
    send_count = counts.get(company["id"], 0)

    render_flow_status(company, latest_proposal, send_count)

    st.markdown("### 1. 連絡先を確認する")
    st.write("まず、問い合わせフォーム・メール・FAXのどれかが使えるか確認します。")
    contact_cols = st.columns(4)
    contact_cols[0].metric("フォーム", "あり" if company["contact_url"] else "未確認")
    contact_cols[1].metric("メール", "あり" if company["email"] else "未確認")
    contact_cols[2].metric("FAX", "あり" if company["fax"] else "未確認")
    contact_cols[3].metric("送信回数", send_count)

    check_url = st.text_input(
        "確認するURL",
        value=company["contact_url"] or company["url"] or "",
        help="通常はそのままで大丈夫です。公式サイトが別に分かる場合だけ変更してください。",
    )
    col_check, col_map = st.columns([1, 1])
    if col_check.button("フォーム・FAXを確認する", type="primary", disabled=not bool(check_url), key=f"easy-check-{company['id']}"):
        with st.spinner("問い合わせ先を確認しています。公式サイトも探します..."):
            result = find_contact_for_company(company, check_url)
            add_form_result(
                company["id"],
                result["form_url"],
                result["fields"],
                result["has_captcha"],
                result["can_autofill"],
                result["notes"],
            )
            email = first_real_email(result.get("emails", []))
            fax = first_value(result.get("faxes", []))
            if result["fields"]:
                update_company_contact(company["id"], email=email, contact_url=result["form_url"], fax=fax)
            elif email or fax:
                update_company_contact(company["id"], email=email, fax=fax)
        st.success("問い合わせ先を保存しました。次は文面を作成してください。")
        st.rerun()
    col_map.link_button("Google Mapで確認", company_maps_url(company))

    st.markdown("### 2. 営業文を作る")
    st.write("フォーム・メールで送る場合は通常文面、FAXで送る場合はFAX文面を作ります。")
    col_proposal, col_fax = st.columns(2)
    if col_proposal.button("フォーム・メール用の文面を作る", type="primary", key=f"easy-proposal-{company['id']}"):
        with st.spinner("営業文を作成しています..."):
            subject, message = generate_proposal(dict(company))
            add_proposal(company["id"], subject, message)
        st.success("文面を保存しました。")
        st.rerun()
    if col_fax.button("FAX用の文面を作る", key=f"easy-fax-{company['id']}"):
        with st.spinner("FAX用の文面を作成しています..."):
            subject, message = generate_fax_proposal(dict(company))
            add_proposal(company["id"], subject, message)
        st.success("FAX用の文面を保存しました。")
        st.rerun()

    if not latest_proposal:
        st.info("まだ文面がありません。上のボタンで文面を作ってください。")
        return

    st.markdown("### 3. 内容を確認して送る")
    st.write("件名と本文をコピーして、フォーム・メール・FAXのいずれかで送ります。")
    st.text_input("件名", latest_proposal["subject"], key=f"easy-subject-{latest_proposal['id']}")
    st.text_area("本文", latest_proposal["message"], height=260, key=f"easy-message-{latest_proposal['id']}")

    send_cols = st.columns(3)
    if company["contact_url"]:
        send_cols[0].link_button("問い合わせフォームを開く", company["contact_url"])
    else:
        send_cols[0].info("フォームURL未取得")
    if company["email"]:
        send_cols[1].link_button("メール下書きを開く", build_mailto(company["email"], latest_proposal["subject"], latest_proposal["message"]))
    else:
        send_cols[1].info("メール未取得")
    if company["fax"]:
        send_cols[2].success(f"FAX番号: {company['fax']}")
    else:
        send_cols[2].info("FAX未取得")

    st.code(f"件名: {latest_proposal['subject']}\n\n{latest_proposal['message']}", language="text")

    st.markdown("### 4. 送ったら記録する")
    st.write("実際に送信した後、必ずここで記録します。次回、いつ・どこに送ったか確認できます。")
    col_channel, col_approach = st.columns(2)
    channel = col_channel.selectbox(
        "送信方法",
        ["問い合わせフォーム", "メール", "FAX", "電話後フォロー", "その他"],
        key=f"easy-channel-{latest_proposal['id']}",
    )
    approach = col_approach.selectbox(
        "今回の切り口",
        ["初回提案", "コスト安定", "欠車リスク対策", "繁忙期対応", "緊急配送", "定期便化", "再送フォロー"],
        key=f"easy-approach-{latest_proposal['id']}",
    )
    note = st.text_input("メモ", placeholder="例: フォームから送信。返信待ち。", key=f"easy-note-{latest_proposal['id']}")
    if st.button("送信済みに記録する", type="primary", key=f"easy-mark-sent-{latest_proposal['id']}"):
        update_company_status(company["id"], "送信済み")
        add_send_log(
            company_id=company["id"],
            proposal_id=latest_proposal["id"],
            channel=channel,
            approach=approach,
            subject=latest_proposal["subject"],
            message=latest_proposal["message"],
            note=note or f"{channel}で送信",
        )
        add_activity(company["id"], "送信済み", note or f"{channel}で送信済みに記録")
        st.success("送信履歴に記録しました。お疲れさまでした。")
        st.rerun()


def render_flow_status(company, latest_proposal, send_count: int) -> None:
    contact_done = bool(company["contact_url"] or company["email"] or company["fax"])
    proposal_done = bool(latest_proposal)
    sent_done = send_count > 0 or company["status"] == "送信済み"
    steps = [
        ("1. 連絡先確認", contact_done),
        ("2. 文面作成", proposal_done),
        ("3. 送信", sent_done),
        ("4. 記録", sent_done),
    ]
    cols = st.columns(4)
    for col, (label, done) in zip(cols, steps):
        if done:
            col.success(f"{label}\n完了")
        else:
            col.info(f"{label}\nこれから")


def render_companies() -> None:
    st.subheader("営業候補一覧")
    cleanup_noise_once()

    with st.expander("古い候補・不要候補の整理"):
        st.caption("求人サイト、企業一覧サイト、自社サイトなど営業対象になりにくい候補をまとめて削除できます。")
        col1, col2 = st.columns([1, 2])
        if col1.button("求人・一覧サイト候補を削除"):
            deleted = delete_companies_by_noise_patterns(NOISE_URL_PATTERNS, NOISE_TEXT_PATTERNS)
            st.success(f"{deleted}件を削除しました。")
            st.rerun()
        delete_all_confirm = col2.checkbox("全営業候補を削除する場合だけチェック")
        if col2.button("営業候補を全削除", disabled=not delete_all_confirm):
            delete_all_companies()
            st.success("営業候補をすべて削除しました。")
            st.rerun()

    status = st.selectbox("ステータス", ["すべて", *STATUSES])
    rows = list_companies(status)
    if not rows:
        st.info("まだ企業データがありません。まずは見込み客検索から始めてください。")
        return

    df = pd.DataFrame([dict(row) for row in rows])
    counts = send_count_by_company()
    df["send_count"] = df["id"].map(counts).fillna(0).astype(int)
    show_dataframe(
        df,
        [
            "id",
            "name",
            "industry",
            "area",
            "need_score",
            "suggested_offer",
            "status",
            "send_count",
            "contact_url",
            "email",
            "fax",
            "latitude",
            "longitude",
            "url",
        ],
    )

    company = select_company(rows)
    if not company:
        return

    st.markdown("#### 事前確認")
    map_url = company_maps_url(company)
    street_view_url = company_street_view_url(company)
    col_map, col_street, col_delete = st.columns([1, 1, 2])
    col_map.link_button("Google Mapで確認", map_url)
    if street_view_url:
        col_street.link_button("ストリートビューで確認", street_view_url)
    else:
        col_street.info("位置情報がある候補はストリートビューを開けます。")
    delete_confirm = col_delete.checkbox("この会社を削除する", key=f"delete-confirm-{company['id']}")
    if col_delete.button("選択中の会社を削除", disabled=not delete_confirm, key=f"delete-company-{company['id']}"):
        delete_company(company["id"])
        st.success("選択中の会社を削除しました。")
        st.rerun()

    col1, col2 = st.columns([1, 2])
    new_status = col1.selectbox("ステータス変更", STATUSES, index=STATUSES.index(company["status"]))
    note = col2.text_input("活動メモ", placeholder="例: フォーム送信済み、返信待ち")
    if st.button("更新"):
        update_company_status(company["id"], new_status)
        if note:
            add_activity(company["id"], new_status, note)
        st.success("更新しました。")
        st.rerun()

    st.markdown("#### 企業メモ")
    st.write(company["summary"] or "概要未登録")
    st.write(f"評価理由: {company['score_reason'] or '-'}")


def render_proposals() -> None:
    st.subheader("提案文生成")
    rows = list_companies()
    company = select_company(rows)
    if not company:
        return

    st.write(f"対象: **{company['name']}** / スコア {company['need_score']}")
    col1, col2 = st.columns(2)
    if col1.button("フォーム・メール用の提案文を生成", type="primary"):
        with st.spinner("企業情報に合わせて提案文を作成しています..."):
            subject, message = generate_proposal(dict(company))
            add_proposal(company["id"], subject, message)
        st.success("提案文を保存しました。")
        st.rerun()
    if col2.button("FAX用の文面を生成"):
        with st.spinner("FAXで読みやすい営業文を作成しています..."):
            subject, message = generate_fax_proposal(dict(company))
            add_proposal(company["id"], subject, message)
        st.success("FAX用の文面を保存しました。")
        st.rerun()

    proposals = list_proposals(company["id"])
    if not proposals:
        st.info("この企業の提案文はまだありません。")
        return

    for proposal in proposals:
        with st.expander(f"v{proposal['version']} / {proposal['subject']}", expanded=True):
            st.text_input("件名", proposal["subject"], key=f"subject-{proposal['id']}")
            st.text_area("本文", proposal["message"], height=280, key=f"message-{proposal['id']}")
            render_send_tools(company, proposal)


def render_forms() -> None:
    st.subheader("問い合わせフォーム確認")
    rows = list_companies()
    if rows:
        st.markdown("#### 一括取得")
        if st.session_state.get("last_form_bulk_summary"):
            st.markdown("#### 前回の一括取得結果")
            st.caption("画面を移動するまで、この結果を確認できます。会社情報にも保存済みです。")
            show_dataframe(pd.DataFrame(st.session_state["last_form_bulk_summary"]))

        only_missing = st.checkbox("フォームURL未取得の会社だけ対象にする", value=True)
        limit = st.number_input("最大取得件数", min_value=1, max_value=100, value=min(10, len(rows)))
        if st.button("検索結果のフォームURLを一括取得", type="primary"):
            targets = [
                row
                for row in rows
                if row["url"] and (not only_missing or not row["contact_url"])
            ][: int(limit)]
            if not targets:
                st.info("取得対象がありません。")
            else:
                progress = st.progress(0)
                status_box = st.empty()
                summary = []
                for index, row in enumerate(targets, start=1):
                    status_box.write(f"{index}/{len(targets)}: {row['name']} のフォームURLを確認中...")
                    result = find_contact_for_company(row, row["url"])
                    add_form_result(
                        row["id"],
                        result["form_url"],
                        result["fields"],
                        result["has_captcha"],
                        result["can_autofill"],
                        result["notes"],
                    )
                    email = first_real_email(result.get("emails", []))
                    fax = first_value(result.get("faxes", []))
                    if result["fields"]:
                        update_company_contact(
                            row["id"],
                            email=email,
                            contact_url=result["form_url"],
                            fax=fax,
                        )
                    elif email or fax:
                        update_company_contact(row["id"], email=email, fax=fax)
                    summary.append(
                        {
                            "会社名": row["name"],
                            "フォームURL": result["form_url"] if result["fields"] else "",
                            "メール": email or "",
                            "FAX": fax or "",
                            "結果": result["notes"],
                        }
                    )
                    progress.progress(index / len(targets))
                status_box.success("一括取得が完了しました。")
                st.session_state["last_form_bulk_summary"] = summary
                show_dataframe(pd.DataFrame(summary))

        st.divider()

    company = select_company(rows)
    if not company:
        return

    target_url = st.text_input("確認するURL", value=company["contact_url"] or company["url"] or "")
    if st.button("フォームを探す", type="primary", disabled=not bool(target_url)):
        with st.spinner("問い合わせページと入力項目を確認しています..."):
            result = find_contact_for_company(company, target_url)
            add_form_result(
                company["id"],
                result["form_url"],
                result["fields"],
                result["has_captcha"],
                result["can_autofill"],
                result["notes"],
            )
            email = first_real_email(result.get("emails", []))
            fax = first_value(result.get("faxes", []))
            if result["fields"]:
                update_company_contact(company["id"], email=email, contact_url=result["form_url"], fax=fax)
            elif email or fax:
                update_company_contact(company["id"], email=email, fax=fax)
        st.success("フォーム確認結果を保存しました。")
        st.rerun()

    forms = list_forms(company["id"])
    for form in forms:
        with st.expander(form["form_url"], expanded=True):
            st.write(f"reCAPTCHA: {'あり' if form['has_captcha'] else 'なし'}")
            st.write(f"下書き自動入力候補: {'可' if form['can_autofill'] else '要確認'}")
            st.write(form["notes"] or "")
            st.success("次にやること: 左メニューの「かんたん営業フロー」を開き、文面を作って送信してください。")
            fields = json.loads(form["fields_json"] or "[]")
            if fields:
                show_form_fields(fields)


def render_send_tools(company: dict, proposal: dict) -> None:
    st.markdown("#### 送信準備")

    email_key = f"email-{company['id']}-{proposal['id']}"
    form_key = f"form-{company['id']}-{proposal['id']}"
    fax_key = f"fax-{company['id']}-{proposal['id']}"
    email = st.text_input("宛先メール", value=company["email"] or "", key=email_key)
    fax = st.text_input("FAX番号", value=company["fax"] or "", key=fax_key)
    contact_url = st.text_input(
        "問い合わせフォームURL",
        value=company["contact_url"] or company["url"] or "",
        key=form_key,
    )
    channel = st.selectbox(
        "送信方法",
        ["問い合わせフォーム", "メール", "FAX", "電話後フォロー", "その他"],
        key=f"channel-{proposal['id']}",
    )
    approach = st.selectbox(
        "今回のアプローチ",
        ["初回提案", "コスト安定", "欠車リスク対策", "繁忙期対応", "緊急配送", "定期便化", "再送フォロー"],
        key=f"approach-{proposal['id']}",
    )

    col1, col2, col3 = st.columns(3)
    if col1.button("連絡先を保存", key=f"save-contact-{proposal['id']}"):
        update_company_contact(company["id"], email=email, contact_url=contact_url, fax=fax)
        st.success("連絡先を保存しました。")
        st.rerun()

    if email:
        mailto = build_mailto(email, proposal["subject"], proposal["message"])
        col2.link_button("メール下書きを開く", mailto)
    else:
        col2.info("メールアドレス未登録")

    if contact_url:
        col3.link_button("フォームを開く", contact_url)
    else:
        col3.info("フォームURL未登録")

    if fax:
        st.info(f"FAX送付先: {fax}")

    st.caption("コピー用")
    st.code(f"件名: {proposal['subject']}\n\n{proposal['message']}", language="text")

    if st.button("送信済みに記録", key=f"mark-sent-{proposal['id']}"):
        update_company_status(company["id"], "送信済み")
        add_send_log(
            company_id=company["id"],
            proposal_id=proposal["id"],
            channel=channel,
            approach=approach,
            subject=proposal["subject"],
            message=proposal["message"],
            note=f"{channel}で送信",
        )
        add_activity(
            company["id"],
            "送信済み",
            f"v{proposal['version']} の提案文を{channel}で送信済みに記録",
        )
        st.success("送信済みに記録しました。")
        st.rerun()


def cleanup_noise_once() -> None:
    if st.session_state.get("noise_cleanup_done"):
        return
    deleted = delete_companies_by_noise_patterns(NOISE_URL_PATTERNS, NOISE_TEXT_PATTERNS)
    st.session_state["noise_cleanup_done"] = True
    if deleted:
        st.success(f"求人サイトなど営業対象外の候補を{deleted}件削除しました。")


def find_contact_for_company(company, target_url: str) -> dict:
    urls = [target_url]
    official_url = find_company_website(company["name"], company["area"] or "")
    if official_url and official_url not in urls:
        urls.append(official_url)

    best_result = None
    for url in urls:
        if not url:
            continue
        result = find_contact_form(url)
        if url != target_url:
            result["notes"] = f"公式サイト候補から再確認: {url} / {result.get('notes', '')}"
        if result.get("fields") and not _is_recruit_form(result.get("form_url", "")):
            return result
        if result.get("faxes") or result.get("emails"):
            best_result = result
        elif best_result is None:
            best_result = result
    return best_result or find_contact_form(target_url)


def _is_recruit_form(url: str) -> bool:
    lowered = url.lower()
    return any(word in lowered for word in ("recruit", "entry", "saiyo", "saiyou"))


def show_dataframe(df: pd.DataFrame, columns: list[str] | None = None) -> None:
    if columns:
        existing_columns = [column for column in columns if column in df.columns]
        display_df = df[existing_columns].copy()
    else:
        display_df = df.copy()
    display_df = display_df.rename(columns=COLUMN_LABELS)
    display_df = display_df.fillna("")

    column_config = {}
    for column_name in ("問い合わせフォームURL", "会社URL"):
        if column_name in display_df.columns:
            column_config[column_name] = st.column_config.LinkColumn(
                column_name,
                display_text="開く",
            )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )


def show_form_fields(fields: list[dict]) -> None:
    df = pd.DataFrame(fields).rename(
        columns={
            "tag": "入力種類",
            "name": "項目名",
            "id": "ID",
            "type": "入力タイプ",
            "label": "画面表示",
            "required": "必須",
        }
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


def row_value(row, key: str, default=None):
    try:
        value = row[key]
    except (KeyError, IndexError, TypeError):
        value = row.get(key, default) if hasattr(row, "get") else default
    return default if value is None else value


def company_maps_url(company) -> str:
    url = str(row_value(company, "url", "") or "")
    if "google.com/maps" in url:
        return url

    latitude = row_value(company, "latitude")
    longitude = row_value(company, "longitude")
    if latitude and longitude:
        return f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"

    query_parts = [
        row_value(company, "name", ""),
        row_value(company, "address", ""),
        row_value(company, "area", ""),
    ]
    query = " ".join(str(part) for part in query_parts if part)
    return f"https://www.google.com/maps/search/?api=1&query={quote(query)}"


def company_street_view_url(company) -> str:
    latitude = row_value(company, "latitude")
    longitude = row_value(company, "longitude")
    if not latitude or not longitude:
        return ""
    return f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={latitude},{longitude}"


def build_mailto(email: str, subject: str, body: str) -> str:
    to = quote(email.strip(), safe="@.,+-_")
    return f"mailto:{to}?subject={quote(subject)}&body={quote(body)}"


def first_real_email(emails: list[str]) -> str | None:
    for email in emails:
        if "example." not in email.lower():
            return email
    return None


def first_value(values: list[str]) -> str | None:
    return values[0] if values else None


def render_send_management() -> None:
    st.subheader("送信管理")
    logs = list_send_logs()
    if not logs:
        st.info("まだ送信履歴がありません。提案文生成画面で送信済みに記録すると、ここに蓄積されます。")
        return

    df = pd.DataFrame([dict(row) for row in logs])
    summary = (
        df.groupby(["company_id", "company_name"], as_index=False)
        .agg(
            send_count=("id", "count"),
            last_sent_at=("sent_at", "max"),
            last_channel=("channel", "last"),
            last_approach=("approach", "last"),
            status=("status", "last"),
            contact_url=("contact_url", "last"),
            email=("email", "last"),
            fax=("fax", "last"),
        )
        .sort_values(["last_sent_at", "send_count"], ascending=[False, False])
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("送信済み会社数", summary["company_id"].nunique())
    col2.metric("総送信回数", len(df))
    col3.metric("複数回送信", int((summary["send_count"] >= 2).sum()))

    st.markdown("#### 会社別送信状況")
    show_dataframe(summary)

    st.markdown("#### 送信履歴")
    show_dataframe(
        df,
        [
            "sent_at",
            "company_name",
            "channel",
            "approach",
            "subject",
            "note",
            "contact_url",
            "email",
            "fax",
        ],
    )

    labels = {
        f"{row['sent_at']} / {row['company_name']} / {row['approach'] or '-'} / {row['subject'] or '-'}": row
        for row in logs
    }
    selected_label = st.selectbox("再送の元にする履歴", list(labels.keys()))
    selected = labels[selected_label]
    company = get_company(selected["company_id"])
    if not company:
        st.warning("対象会社が見つかりません。")
        return

    st.markdown("#### 別アプローチで再送文を作成")
    approach = st.selectbox(
        "次の切り口",
        [
            "前回より短く、情報交換ベースで再送",
            "2024年問題と欠車リスク対策を中心に再送",
            "繁忙期・急な物量増加への備えとして再送",
            "緊急配送・チャーター便の対応力を中心に再送",
            "定期便化による配送コスト安定を中心に再送",
            "相手の業種に合わせて、より具体的な利用シーンで再送",
        ],
    )
    custom_approach = st.text_input("自由入力の切り口", placeholder="例: 冷凍冷蔵品の店舗納品に絞って提案")
    final_approach = custom_approach.strip() or approach

    if st.button("別アプローチ文面を生成", type="primary"):
        with st.spinner("過去文面と重ならない再送文を作成しています..."):
            subject, message = generate_resend_proposal(
                dict(company),
                selected["subject"] or "",
                selected["message"] or "",
                final_approach,
            )
            add_proposal(company["id"], subject, message)
        st.success("再送用の提案文を保存しました。提案文生成画面から送信準備できます。")
        st.rerun()


def render_activities() -> None:
    st.subheader("活動履歴")
    activities = list_activities()
    if not activities:
        st.info("活動履歴はまだありません。")
        return
    show_dataframe(pd.DataFrame([dict(row) for row in activities]))


def render_help() -> None:
    st.subheader("HELP / 操作マニュアル")

    st.markdown(
        """
### このツールでできること

営業スタッフが常駐していなくても、運送会社の新規営業を半自動で回すための管理ツールです。

主な流れは次の通りです。

1. 見込み客を検索する
2. 会社一覧で候補を確認する
3. 問い合わせフォームURLを取得する
4. AI提案文を作る
5. フォームまたはメールで送る
6. 送信済みに記録する
7. 送信管理で過去履歴を見て、別アプローチで再送する

FAX番号が取れた会社には、FAX用の文面を生成して送付履歴として管理できます。
"""
    )

    with st.expander("1. 初期設定", expanded=True):
        st.markdown(
            """
### SERPER_API_KEY

会社検索に使います。設定しないと実在企業の検索はできません。

`.env` に以下のように設定します。

```env
SERPER_API_KEY=あなたのSerper APIキー
```

設定後はアプリを再起動してください。

```powershell
python -m streamlit run main.py
```

### OPENAI_API_KEY

AIで営業文を本格生成したい場合に使います。未設定でもテンプレート文面で動きます。

```env
OPENAI_API_KEY=あなたのOpenAI APIキー
```

### APP_PASSWORD

管理画面をクライアントに公開するときのアクセスパスワードです。

```env
APP_PASSWORD=クライアントに共有するパスワード
```

Streamlit Cloudに公開する場合は `.env` ではなく、Secretsに設定します。
"""
        )

    with st.expander("2. 見込み客検索"):
        st.markdown(
            """
左メニューの **見込み客検索** を開きます。

入力例:

- 業種・キーワード: `食品メーカー`
- エリア: `埼玉県`
- 取得件数: `10`

**検索して保存** を押すと、実在会社の候補が保存されます。

検索結果には、会社名、Webサイト、住所、電話番号、営業優先度などが入ります。

検索キーワードはプリセットから選ぶか、自由検索欄に入力できます。
求人情報や企業一覧サイトが混ざった場合は、営業候補一覧の整理ボタンで削除できます。
"""
        )

    with st.expander("3. 営業候補一覧"):
        st.markdown(
            """
左メニューの **営業候補一覧** で、保存した会社を確認します。

確認できる項目:

- 会社名
- 業種
- エリア
- 営業スコア
- ステータス
- 送信回数
- 問い合わせフォームURL
- メールアドレス
- FAX番号
- 会社URL

会社を選ぶと、Google Mapで所在地を確認できます。
位置情報が取得できている会社は、ストリートビュー確認リンクも表示されます。

ステータスは、`未確認`、`送信候補`、`送信済み`、`返信あり`、`商談化`、`見送り`、`NG` で管理できます。
"""
        )

    with st.expander("4. 問い合わせフォームURL取得"):
        st.markdown(
            """
左メニューの **問い合わせフォーム確認** を開きます。

### 一括取得

検索結果の会社に対して、フォームURLをまとめて探せます。

1. **フォームURL未取得の会社だけ対象にする** をON
2. **最大取得件数** を指定
3. **検索結果のフォームURLを一括取得** を押す

取得できたURLは会社情報の `contact_url` に保存されます。

### 個別取得

会社を選んで **フォームを探す** を押すと、その会社だけ確認できます。
"""
        )

    with st.expander("5. 提案文生成と送信"):
        st.markdown(
            """
左メニューの **提案文生成** を開きます。

1. 会社を選ぶ
2. **フォーム・メール用の提案文を生成** または **FAX用の文面を生成** を押す
3. 件名と本文を確認する
4. 送信方法とアプローチを選ぶ
5. **フォームを開く** または **メール下書きを開く**
6. 実際に送信したら **送信済みに記録**

このツールは大量自動送信ではなく、最後に人間が確認して送る前提です。
"""
        )

    with st.expander("6. 送信管理・再送"):
        st.markdown(
            """
左メニューの **送信管理** で、過去の送信履歴を確認できます。

確認できる内容:

- いつ送ったか
- どこの会社に送ったか
- 送信方法
- アプローチ
- 件名
- 会社別の送信回数

過去履歴を選び、別アプローチを指定して **別アプローチ文面を生成** を押すと、再送用の提案文が作れます。

例:

- 前回より短く、情報交換ベースで再送
- 2024年問題と欠車リスク対策を中心に再送
- 繁忙期・急な物量増加への備えとして再送
- 緊急配送・チャーター便の対応力を中心に再送
- 定期便化による配送コスト安定を中心に再送
"""
        )

    with st.expander("7. よくある困りごと"):
        st.markdown(
            """
### 検索できない

`.env` に `SERPER_API_KEY` が設定されているか確認してください。設定後はアプリ再起動が必要です。

### フォームURLが見つからない

会社サイトによっては問い合わせフォームがない、またはJavaScriptで表示される場合があります。その場合は会社URLを開いて手動確認してください。

### メール下書きが開かない

PC側に既定のメールアプリが設定されていない可能性があります。その場合は、件名・本文をコピーしてGmailやOutlookに貼り付けてください。

### サンプルURLが表示される

古いデモデータが残っている可能性があります。現在の実装ではサンプル会社は自動生成されません。
"""
        )

    with st.expander("8. クライアントに公開する"):
        st.markdown(
            """
公開は **Streamlit Community Cloud + Supabase** の構成がおすすめです。

手順:

1. GitHubにコードをアップロード
2. Streamlit Community Cloudで `main.py` を指定してデプロイ
3. Secretsに `DATABASE_URL`、`SERPER_API_KEY`、`OPENAI_API_KEY`、`APP_PASSWORD` を設定
4. 発行された `https://...streamlit.app` のURLをクライアントに共有
5. `APP_PASSWORD` も別途共有

注意:

- `.env` はGitHubに上げない
- `sales_ai.sqlite3` はGitHubに上げない
- SupabaseのDBパスワードはチャットやメールにそのまま貼らない
"""
        )

    st.info("基本は、検索 → フォームURL取得 → 提案文生成 → 送信済みに記録 → 送信管理で再送、の順番です。")


def select_company(rows) -> dict | None:
    if not rows:
        st.info("企業データがありません。")
        return None
    labels = {f"{row['id']}: {row['name']}（{row['need_score']}点）": row for row in rows}
    selected = st.selectbox("企業を選択", list(labels.keys()))
    return labels[selected]


if __name__ == "__main__":
    main()
