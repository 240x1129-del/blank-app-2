import streamlit as st
from datetime import datetime, timedelta, timezone, date
import pandas as pd
from supabase import create_client

# =========================
# Timezone (JST)
# =========================
JST = timezone(timedelta(hours=9))

# =========================
# Page config
# =========================
st.set_page_config(page_title="収支管理アプリ", layout="wide")
st.title("収支管理アプリ")

# =========================
# Supabase connection (Secrets)
# =========================
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# =========================
# DB functions
# =========================
def add_expense(dt, category, amount, memo):
    supabase.table("expenses").insert({
        "dt": dt.isoformat(),
        "category": category,
        "amount": int(amount),
        "memo": memo
    }).execute()

def delete_expense(expense_id):
    supabase.table("expenses").delete().eq("id", expense_id).execute()

def fetch_month_expenses(year, month):
    start = datetime(year, month, 1, tzinfo=JST)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=JST)
    else:
        end = datetime(year, month + 1, 1, tzinfo=JST)

    res = (
        supabase.table("expenses")
        .select("*")
        .gte("dt", start.isoformat())
        .lt("dt", end.isoformat())
        .order("dt", desc=True)
        .execute()
    )
    return res.data

def get_today_spent(today: date):
    start = datetime(today.year, today.month, today.day, tzinfo=JST)
    end = start + timedelta(days=1)

    res = (
        supabase.table("expenses")
        .select("amount")
        .gte("dt", start.isoformat())
        .lt("dt", end.isoformat())
        .execute()
    )

    return sum(r["amount"] for r in res.data) if res.data else 0

# =========================
# Header info
# =========================
now_jst = datetime.now(JST)
st.write("取得時刻（JST）:", now_jst.strftime("%Y-%m-%d %H:%M:%S"))

# =========================
# Inputs (goal + days)
# =========================
goal = st.number_input("目標貯金額（円）", min_value=0, value=30000, step=1000)
days_left = st.number_input("今月残り日数（例）", min_value=1, value=30, step=1)
daily_limit = goal / days_left if days_left > 0 else 0

st.divider()

# =========================
# Today's judgement
# =========================
st.subheader("今日の判定")
today_jst = datetime.now(JST).date()
today_spent = get_today_spent(today_jst)

if today_spent <= daily_limit:
    st.success(f"黒字（OK）：今日の支出 {today_spent:,} 円 / 目安 {daily_limit:,.0f} 円")
else:
    over = today_spent - daily_limit
    st.error(f"赤字（使いすぎ）：今日の支出 {today_spent:,} 円（{over:,.0f} 円オーバー）")

st.caption(f"※ 目安 = {goal:,} ÷ {days_left} = {daily_limit:,.2f} 円/日")

st.divider()

# =========================
# Add expense form
# =========================
st.subheader("支出を追加")

with st.form("add_form", clear_on_submit=True):
    dt = st.datetime_input("日時（JST）", value=datetime.now(JST))
    category = st.selectbox("カテゴリ", ["食費", "日用品", "交通", "娯楽", "交際", "医療", "その他"])
    amount = st.number_input("金額（円）", min_value=0, value=500, step=10)
    memo = st.text_input("メモ（任意）", "")
    submitted = st.form_submit_button("追加")

    if submitted:
        add_expense(dt, category, amount, memo)
        st.success("追加しました")
        st.rerun()

st.divider()

# =========================
# Show current month expenses
# =========================
st.subheader("今月の支出一覧")

rows = fetch_month_expenses(now_jst.year, now_jst.month)

if rows:
    df = pd.DataFrame(rows)
    df["dt"] = pd.to_datetime(df["dt"])

    st.dataframe(
        df[["id", "dt", "category", "amount", "memo"]],
        use_container_width=True
    )

    delete_id = st.number_input("削除するID", min_value=0, step=1)
    if st.button("このIDを削除"):
        delete_expense(int(delete_id))
        st.success("削除しました")
        st.rerun()
else:
    st.info("今月の支出はまだありません。")
