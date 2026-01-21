import streamlit as st
import sqlite3
from pathlib import Path
from datetime import datetime, date
import pandas as pd

st.set_page_config(page_title="収支管理", layout="wide")
st.title("収支管理アプリ")

# --- 永続DB（ファイル） ---
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "expenses.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()  # ← unmatched ')' を防ぐ正しい書き方
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
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (dt, category, amount, memo) VALUES (?, ?, ?, ?)",
        (dt.isoformat(), category, amount, memo)
    )
    conn.commit()
    conn.close()

def load_month_rows(year: int, month: int):
    conn = get_conn()
    cur = conn.cursor()
    start = datetime(year, month, 1).isoformat()
    if month == 12:
        end = datetime(year + 1, 1, 1).isoformat()
    else:
        end = datetime(year, month + 1, 1).isoformat()

    cur.execute(
        "SELECT dt, category, amount, memo FROM expenses WHERE dt >= ? AND dt < ? ORDER BY dt DESC",
        (start, end)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_today_spent(today: date):
    conn = get_conn()
    cur = conn.cursor()
    start = datetime(today.year, today.month, today.day).isoformat()
    end = datetime(today.year, today.month, today.day, 23, 59, 59).isoformat()
    cur.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE dt >= ? AND dt <= ?", (start, end))
    total = cur.fetchone()[0]
    conn.close()
    return int(total)

# 初期化
init_db()

# --- 目標から1日予算を出す例（簡易） ---
target = st.number_input("目標貯金額（円）", min_value=0, value=30000, step=1000)
days = st.number_input("今月残り日数（例）", min_value=1, value=30, step=1)
daily_limit = target / days if days else 0

today = date.today()
today_spent = get_today_spent(today)

st.subheader("今日の判定")
if today_spent <= daily_limit:
    st.success(f"黒字（OK）：今日の支出 {today_spent:,} 円 / 目安 {daily_limit:,.0f} 円")
else:
    over = today_spent - daily_limit
    st.error(f"赤字（使いすぎ）：今日の支出 {today_spent:,} 円（{over:,.0f} 円オーバー）")

st.divider()

# --- 支出追加 ---
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

# --- 今月一覧 ---
st.subheader("今月の支出一覧")
rows = load_month_rows(today.year, today.month)
if rows:
    df = pd.DataFrame(rows, columns=["dt", "category", "amount", "memo"])
    df["dt"] = pd.to_datetime(df["dt"])
    st.dataframe(df, use_container_width=True)
else:
    st.info("今月の支出はまだありません。")
