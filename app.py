import streamlit as st
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="GSHEETS 連線測試（加強版）", page_icon="✅", layout="wide")
st.title("✅ Google Sheets 連線測試（加強版）")

SHEET_URL = "https://docs.google.com/spreadsheets/d/1Pz7z9CdU8MODTdXbckXCnI0NpjXquZDcZCC-DTOen3o/edit"
WORKSHEET = "enrollments"

st.markdown(f"目前連到的試算表：[{SHEET_URL}]({SHEET_URL})")
st.caption("請確認你在 Google Drive 打開的就是這一份，並且切到 enrollments 分頁。")

try:
    from streamlit_gsheets import GSheetsConnection
except Exception:
    st.error("缺少套件 streamlit-gsheets，請確認 requirements.txt 有安裝 streamlit-gsheets==0.1.0")
    st.stop()

@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

conn = get_conn()

REQUIRED_COLS = [
    "id","timestamp","student_name","gender","birth_date",
    "desired_class","start_month","guardian_name","guardian_relation",
    "phone","email","address","notes","status"
]

def read_sheet_no_cache():
    # 這裡不使用 cache_data，確保每次都重新讀
    df = conn.read(worksheet=WORKSHEET)
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=REQUIRED_COLS)
    for c in REQUIRED_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[REQUIRED_COLS]
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    df["timestamp"] = df["timestamp"].astype(str)
    return df

st.subheader("1) 重新讀取（即時）")
if st.button("🔄 重新讀取 Google 試算表", use_container_width=True):
    st.session_state["_force_refresh"] = str(time.time())

df = read_sheet_no_cache()
st.success(f"✅ 讀取成功，目前筆數：{len(df)}")
st.dataframe(df.tail(20), use_container_width=True, hide_index=True)

st.divider()

st.subheader("2) 寫入測試（新增一筆唯一資料）")
st.caption("按下後會新增一筆資料，並且立刻再讀回來確認最後一筆是否出現在 Google 試算表中。")

if st.button("➕ 新增一筆 TEST（含時間戳）", use_container_width=True):
    try:
        df2 = read_sheet_no_cache().copy()

        new_id = 1 if len(df2) == 0 else int(df2["id"].max()) + 1
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        marker = f"TEST幼兒_{datetime.now().strftime('%H%M%S')}"

        new_row = {
            "id": new_id,
            "timestamp": ts,
            "student_name": marker,
            "gender": "不方便透露",
            "birth_date": "2022-01-01",
            "desired_class": "不確定",
            "start_month": "2026-09",
            "guardian_name": "TEST家長",
            "guardian_relation": "其他",
            "phone": "0900000000",
            "email": "",
            "address": "",
            "notes": "加強版連線測試資料，可刪",
            "status": "新送出"
        }

        df2 = pd.concat([df2, pd.DataFrame([new_row])], ignore_index=True)

        # 寫回整張表（最穩）
        conn.update(worksheet=WORKSHEET, data=df2)

        st.success(f"✅ 已寫入：{marker}")
        st.info("等待 2 秒後重新讀取，確認 Google 端也看得到…")
        time.sleep(2)

        df3 = read_sheet_no_cache()
        st.subheader("3) 寫入後再讀回確認")
        st.write("最後 3 筆：")
        st.dataframe(df3.tail(3), use_container_width=True, hide_index=True)

        # 強提示：請用 Google Sheet 搜尋 marker
        st.warning(f"請到 Google 試算表用 Ctrl+F 搜尋：{marker}（最準）")

    except Exception as e:
        st.error("❌ 寫入或回讀失敗")
        st.code(str(e))
