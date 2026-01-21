import streamlit as st
import sqlite3
from datetime import date, datetime
import calendar

st.set_page_config(page_title="収支管理アプリ", layout="wide")
st.title("収支管理アプリ（目標貯金から1日予算を自動提示）")

DB_PATH = "data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT NOT NULL,
            category TEXT NOT NULL,
            amount INTEGER NOT NULL,
            memo TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_expense(dt: datetime, category: str, amount: int, memo: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (dt, category, amount, memo) VALUES (?, ?, ?, ?)",
        (dt.isoformat(), category, amount, memo)
    )
    conn.commit()
    conn.close()

def get_expenses_for_month(year: int, month: int):
    start = datetime(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor)
    cur.execute(
        "SELECT dt, category, amount, memo FROM expenses WHERE dt BETWEEN ? AND ? ORDER BY dt ASC",
        (start.isoformat(), end.isoformat())
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_today_spent(today: date):
    start = datetime(today.year, today.month, today.day, 0, 0, 0)
    end = datetime(today.year, today.month, today.day, 23, 59, 59)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE dt BETWEEN ? AND ?",
        (start.isoformat(), end.isoformat())
    )
    total = cur.fetchone()[0]
    conn.close()
    return int(total)

init_db()

# ---- 設定（左）----
with st.sidebar:
    st.header("今月の設定")

    income = st.number_input("今月の収入（円）", min_value=0, value=200000, step=1000)
    fixed = st.number_input("固定費（家賃/通信など）（円）", min_value=0, value=80000, step=1000)
    goal_saving = st.number_input("目標貯金額（円）", min_value=0, value=30000, step=1000)

    today = date.today()
    y, m = today.year, today.month
    last_day = calendar.monthrange(y, m)[1]
    days_left = (date(y, m, last_day) - today).days + 1  # 今日を含む

    st.divider()
    st.write("今月:", f"{y}-{m:02d}")
    st.write("残り日数:", days_left, "日")

# ---- 計算（上）----
spendable = max(0, int(income - fixed - goal_saving))  # 使える上限（マイナスは0扱い）
rows = get_expenses_for_month(y, m)
month_spent = sum(r[2] for r in rows)
remaining_budget = max(0, spendable - month_spent)

daily_limit = remaining_budget / days_left if days_left > 0 else 0
today_spent = get_today_spent(today)

colA, colB, colC, colD = st.columns(4)
colA.metric("今月使える上限", f"{spendable:,} 円")
colB.metric("今月の支出合計", f"{month_spent:,} 円")
colC.metric("残り予算", f"{remaining_budget:,} 円")
colD.metric("今日の目安（1日上限）", f"{daily_limit:,.0f} 円")

st.divider()

# ---- 判定（中）----
st.subheader("今日の判定")
if today_spent <= daily_limit:
    st.success(f"黒字（OK）: 今日の支出 {today_spent:,} 円 / 目安 {daily_limit:,.0f} 円")
else:
    over = today_spent - daily_limit
    st.error(f"赤字（使いすぎ）: 今日の支出 {today_spent:,} 円（{over:,.0f} 円オーバー）")

# ---- 支出入力（右）----
st.subheader("支出を追加")
with st.form("add_form", clear_on_submit=True):
    dt = st.datetime_input("日時", value=datetime.now())
    category = st.selectbox("カテゴリ", ["食費", "日用品", "交通", "娯楽", "交際", "医療", "その他"])
    amount = st.number_input("金額（円）", min_value=0, value=500, step=10)
    memo = st.text_input("メモ（任意）")
    submitted = st.form_submit_button("追加")

    if submitted:
        add_expense(dt, category, int(amount), memo)
        st.success("追加しました。")
        st.rerun()

st.divider()

# ---- 表示（下）----
st.subheader("今月の支出一覧")
if rows:
    import pandas as pd
    df = pd.DataFrame(rows, columns=["dt", "category", "amount", "memo"])
    df["dt"] = pd.to_datetime(df["dt"])
    st.dataframe(df, use_container_width=True)
else:
    st.info("今月の支出はまだありません。")
