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
)
from form_finder import find_contact_form
from lead_search import search_companies
from proposal_generator import generate_proposal, generate_resend_proposal


STATUSES = ["未確認", "送信候補", "送信済み", "返信あり", "商談化", "見送り", "NG"]


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
        ["見込み客検索", "営業候補一覧", "提案文生成", "問い合わせフォーム確認", "送信管理", "活動履歴", "HELP"],
    )

    if menu == "見込み客検索":
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
        if password == settings.app_password:
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
    keyword = col1.text_input("業種・キーワード", value="建材メーカー 定期配送")
    area = col2.text_input("エリア", value="群馬県")
    num = col3.number_input("取得件数", min_value=1, max_value=50, value=20)

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
            count = upsert_companies(companies)
        st.success(f"{count}件を保存しました。")
        st.dataframe(pd.DataFrame(companies), use_container_width=True)


def render_companies() -> None:
    st.subheader("営業候補一覧")
    status = st.selectbox("ステータス", ["すべて", *STATUSES])
    rows = list_companies(status)
    if not rows:
        st.info("まだ企業データがありません。まずは見込み客検索から始めてください。")
        return

    df = pd.DataFrame([dict(row) for row in rows])
    counts = send_count_by_company()
    df["send_count"] = df["id"].map(counts).fillna(0).astype(int)
    st.dataframe(
        df[
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
                "url",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    company = select_company(rows)
    if not company:
        return

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
    if st.button("AI提案文を生成", type="primary"):
        with st.spinner("企業情報に合わせて提案文を作成しています..."):
            subject, message = generate_proposal(dict(company))
            add_proposal(company["id"], subject, message)
        st.success("提案文を保存しました。")
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
                    result = find_contact_form(row["url"])
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
                st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)
                st.rerun()

        st.divider()

    company = select_company(rows)
    if not company:
        return

    target_url = st.text_input("確認するURL", value=company["contact_url"] or company["url"] or "")
    if st.button("フォームを探す", type="primary", disabled=not bool(target_url)):
        with st.spinner("問い合わせページと入力項目を確認しています..."):
            result = find_contact_form(target_url)
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
            fields = json.loads(form["fields_json"] or "[]")
            if fields:
                st.dataframe(pd.DataFrame(fields), use_container_width=True, hide_index=True)


def render_send_tools(company: dict, proposal: dict) -> None:
    st.markdown("#### 送信準備")

    email_key = f"email-{company['id']}-{proposal['id']}"
    form_key = f"form-{company['id']}-{proposal['id']}"
    email = st.text_input("宛先メール", value=company["email"] or "", key=email_key)
    contact_url = st.text_input(
        "問い合わせフォームURL",
        value=company["contact_url"] or company["url"] or "",
        key=form_key,
    )
    channel = st.selectbox(
        "送信方法",
        ["問い合わせフォーム", "メール", "電話後フォロー", "その他"],
        key=f"channel-{proposal['id']}",
    )
    approach = st.selectbox(
        "今回のアプローチ",
        ["初回提案", "コスト安定", "欠車リスク対策", "繁忙期対応", "緊急配送", "定期便化", "再送フォロー"],
        key=f"approach-{proposal['id']}",
    )

    col1, col2, col3 = st.columns(3)
    if col1.button("連絡先を保存", key=f"save-contact-{proposal['id']}"):
        update_company_contact(company["id"], email=email, contact_url=contact_url)
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
        )
        .sort_values(["last_sent_at", "send_count"], ascending=[False, False])
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("送信済み会社数", summary["company_id"].nunique())
    col2.metric("総送信回数", len(df))
    col3.metric("複数回送信", int((summary["send_count"] >= 2).sum()))

    st.markdown("#### 会社別送信状況")
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.markdown("#### 送信履歴")
    st.dataframe(
        df[
            [
                "sent_at",
                "company_name",
                "channel",
                "approach",
                "subject",
                "note",
                "contact_url",
                "email",
            ]
        ],
        use_container_width=True,
        hide_index=True,
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
    st.dataframe(pd.DataFrame([dict(row) for row in activities]), use_container_width=True, hide_index=True)


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
- 会社URL

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
2. **AI提案文を生成** を押す
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
