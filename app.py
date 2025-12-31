import streamlit as st
import pandas as pd
from datetime import datetime, date
from pathlib import Path

# =========================
# 基本設定
# =========================
st.set_page_config(page_title="小太陽｜收費記錄（本機版）", page_icon="🧾", layout="wide")
st.title("🧾 小太陽｜收費記錄（本機 CSV 版）")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "payments.csv"

COLUMNS = ["timestamp", "month", "class", "student", "item", "fee", "note"]

def month_str(d: date) -> str:
    return d.strftime("%Y-%m")

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def load_data() -> pd.DataFrame:
    if not DATA_FILE.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(DATA_FILE)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df["fee"] = pd.to_numeric(df["fee"], errors="coerce").fillna(0).astype(int)
    return df[COLUMNS]

def save_data(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def add_row(row: dict):
    df = load_data()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_data(df)

# =========================
# Sidebar：新增收費
# =========================
st.sidebar.header("➕ 新增收費")

default_month = month_str(date.today())
month = st.sidebar.text_input("月份（YYYY-MM）", value=default_month)

class_name = st.sidebar.selectbox("班級", ["大寶班", "小寶班", "小貝班"])
student = st.sidebar.text_input("學生姓名", placeholder="例如：王小明")
item = st.sidebar.selectbox("項目", ["月費", "註冊費", "餐費", "教材費", "其他"])
fee = st.sidebar.number_input("金額", min_value=0, step=100, value=3000)
note = st.sidebar.text_input("備註（可留空）", placeholder="例如：補繳、折抵、轉帳末五碼...")

if st.sidebar.button("✅ 送出新增", use_container_width=True):
    if not student.strip():
        st.sidebar.error("請輸入學生姓名")
    else:
        add_row({
            "timestamp": now_str(),
            "month": month.strip(),
            "class": class_name,
            "student": student.strip(),
            "item": item,
            "fee": int(fee),
            "note": note.strip()
        })
        st.sidebar.success("已新增！")
        st.rerun()

# =========================
# 主畫面：查詢與統計
# =========================
df = load_data()

st.caption(f"目前資料筆數：{len(df)}（檔案：{DATA_FILE.as_posix()}）")
st.divider()

# 篩選
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    months = sorted(df["month"].unique().tolist())[::-1] if len(df) else [default_month]
    q_month = st.selectbox("查詢月份", months)
with col2:
    q_class = st.selectbox("查詢班級", ["全部", "大寶班", "小寶班", "小貝班"])
with col3:
    keyword = st.text_input("快速搜尋（學生/備註）", placeholder="輸入關鍵字...")

filtered = df.copy()
if len(filtered):
    filtered = filtered[filtered["month"] == q_month]
    if q_class != "全部":
        filtered = filtered[filtered["class"] == q_class]
    if keyword.strip():
        k = keyword.strip()
        filtered = filtered[
            filtered["student"].astype(str).str.contains(k, na=False) |
            filtered["note"].astype(str).str.contains(k, na=False)
        ]

# KPI
k1, k2, k3 = st.columns(3)
k1.metric("筆數", f"{len(filtered)}")
k2.metric("金額合計", f"{int(filtered['fee'].sum()) if len(filtered) else 0:,} 元")
k3.metric("學生數（不重複）", f"{int(filtered['student'].nunique()) if len(filtered) else 0} 人")

st.subheader("📋 紀錄列表")
st.dataframe(filtered.sort_values("timestamp", ascending=False), use_container_width=True, hide_index=True)

st.subheader("📥 匯出")
csv_bytes = filtered.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
st.download_button("下載目前篩選結果 CSV", data=csv_bytes, file_name=f"payments_{q_month}.csv", mime="text/csv")
