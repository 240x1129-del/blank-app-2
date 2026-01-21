import streamlit as st
import sqlite3
from datetime import datetime, timedelta, timezone, date
import pandas as pd

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
# SQLite (persistent)
# Streamlit Cloud でも Codespaces でもファイルは残る前提
# ただし Cloud の挙動次第では再デプロイで消えることがあるので、
# 課題用ならまずこれでOK。さらに確実にするなら外部DB化。
# =========================
DB_PATH = "expenses.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dt TEXT NOT NULL,        -- ISO文字列で保存（JSTのローカル時刻）
            category TEXT NOT NULL,
            amount INTEGER NOT NULL,
            memo TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def add_expense(dt: datetime, category: str, amount: int, memo: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (dt, category, amount, memo) VALUES (?, ?, ?, ?)",
        (dt.strftime("%Y-%m-%d %H:%M:%S"), category, int(amount), memo),
    )
    conn.commit()
    conn.close()

def delete_expense(expense_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

def fetch_month_expenses(year: int, month: int):
    # JSTの「その月」範囲
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=JST)
    if month == 12:
        end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=JST)
    else:
        end = datetime(year, month + 1, 1, 0, 0, 0, tzinfo=JST)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, dt, category, amount, memo FROM expenses WHERE dt >= ? AND dt < ? ORDER BY dt DESC",
        (start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")),
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_today_spent(today: date) -> int:
    # 今日(JST)の 00:00:00 〜 23:59:59
    start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=JST)
    end = start + timedelta(days=1)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE dt >= ? AND dt < ?",
        (start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")),
    )
    total = cur.fetchone()[0]
    conn.close()
    return int(total)

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

st.caption(f"※ 目安（1日あたり） = 目標貯金額 {goal:,} ÷ 残り日数 {days_left} = {daily_limit:,.2f} 円/日")

st.divider()

# =========================
# Add expense form
# =========================
st.subheader("支出を追加")

with st.form("add_form", clear_on_submit=True):
    dt = st.datetime_input("日時（JST）", value=datetime.now(JST))
    category = st.selectbox("カテゴリ", ["食費", "日用品", "交通", "娯楽", "交際", "医療", "その他"])
    amount = st.number_input("金額（円）", min_value=0, value=500, step=10)
    memo = st.text_input("メモ（任意）", value="")
    submitted = st.form_submit_button("追加")

    if submitted:
        add_expense(dt, category, int(amount), memo)
        st.success("追加しました。")
        st.rerun()

st.divider()

# =========================
# Show current month expenses
# =========================
st.subheader("今月の支出一覧")

rows = fetch_month_expenses(now_jst.year, now_jst.month)

if rows:
    df = pd.DataFrame(rows, columns=["id", "dt", "category", "amount", "memo"])
    df["dt"] = pd.to_datetime(df["dt"])

    st.dataframe(
        df[["dt", "category", "amount", "memo"]],
        use_container_width=True
    )

    st.subheader("削除")
    delete_id = st.number_input("削除するID（上の一覧の id ）", min_value=0, value=0, step=1)
    if st.button("このIDを削除"):
        if delete_id == 0:
            st.warning("IDが0のままです。削除したいIDを入力してね。")
        else:
            delete_expense(int(delete_id))
            st.success(f"ID={int(delete_id)} を削除しました。")
            st.rerun()
else:
    st.info("今月の支出はまだありません。")
