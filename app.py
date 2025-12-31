import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="GSHEETS 連線測試", page_icon="✅", layout="wide")
st.title("✅ Google Sheets 連線測試")

# 1) 連線
try:
    from streamlit_gsheets import GSheetsConnection
except Exception as e:
    st.error("缺少套件 streamlit-gsheets，請確認 requirements.txt 有安裝 streamlit-gsheets==0.1.0")
    st.stop()

@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

conn = get_conn()

# 2) 讀取
st.subheader("1) 讀取 enrollments 工作表")
try:
    df = conn.read(worksheet="enrollments")
    if df is None or len(df) == 0:
        st.info("讀取成功，但目前工作表是空的（或只有表頭）。")
        df = pd.DataFrame(columns=[
            "id","timestamp","student_name","gender","birth_date",
            "desired_class","start_month","guardian_name","guardian_relation",
            "phone","email","address","notes","status"
        ])
    st.success("✅ 讀取成功")
    st.dataframe(df, use_container_width=True, hide_index=True)
except Exception as e:
    st.error("❌ 讀取失敗（多半是：Secrets 格式、工作表名稱、或未分享給 service account）")
    st.code(str(e))
    st.stop()

st.divider()

# 3) 寫入測試
st.subheader("2) 寫入測試（新增一筆測試資料）")
st.caption("按下按鈕後，會在表格最後新增一筆 TEST 資料。")

if st.button("➕ 新增 TEST 資料", use_container_width=True):
    try:
        df2 = df.copy()
        # 確保欄位存在
        required_cols = [
            "id","timestamp","student_name","gender","birth_date",
            "desired_class","start_month","guardian_name","guardian_relation",
            "phone","email","address","notes","status"
        ]
        for c in required_cols:
            if c not in df2.columns:
                df2[c] = ""

        new_id = 1 if len(df2) == 0 else int(pd.to_numeric(df2["id"], errors="coerce").fillna(0).max()) + 1
        new_row = {
            "id": new_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "student_name": "TEST幼兒",
            "gender": "不方便透露",
            "birth_date": "2022-01-01",
            "desired_class": "不確定",
            "start_month": "2026-09",
            "guardian_name": "TEST家長",
            "guardian_relation": "其他",
            "phone": "0900000000",
            "email": "",
            "address": "",
            "notes": "這是連線測試資料，可刪",
            "status": "新送出"
        }

        df2 = pd.concat([df2, pd.DataFrame([new_row])], ignore_index=True)

        # ✅ 寫回整張表（簡單穩定）
        conn.update(worksheet="enrollments", data=df2)

        st.success("✅ 寫入成功！請到 Google 試算表確認最後一列出現 TEST 資料。")
        st.rerun()

    except Exception as e:
        st.error("❌ 寫入失敗（多半是：沒有把試算表分享給 service account『編輯者』）")
        st.code(str(e))
