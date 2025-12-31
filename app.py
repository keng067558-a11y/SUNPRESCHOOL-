import streamlit as st
import pandas as pd
from datetime import date, datetime
import re
import json

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="小太陽｜新生登記管理系統",
    page_icon="📝",
    layout="wide"
)

# =========================
# Apple-style UI
# =========================
st.markdown("""
<style>
:root{
  --bg:#F5F5F7; --card:#FFFFFF; --text:#1D1D1F; --muted:#6E6E73;
  --line:rgba(0,0,0,0.06); --shadow:0 10px 30px rgba(0,0,0,0.08); --r:18px;
}
.stApp{
  background:var(--bg);
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI","Noto Sans TC","Microsoft JhengHei",sans-serif;
}
.block-container{ max-width:1200px; padding-top:1.4rem; }
.apple-card{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:var(--r);
  box-shadow:var(--shadow);
  padding:20px;
  margin-bottom:18px;
}
.stButton>button{
  border-radius:14px;
  padding:10px 16px;
  background:#111;
  color:#fff;
  font-weight:800;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="apple-card">
  <h2>📝 小太陽｜新生登記管理系統</h2>
  <p style="color:#6E6E73">家長填寫 ➜ 行政後台追蹤（雙狀態＋重要性）</p>
</div>
""", unsafe_allow_html=True)

# =========================
# Google Sheet 設定
# =========================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Pz7z9CdU8MODTdXbckXCnI0NpjXquZDcZCC-DTOen3o/edit"
WORKSHEET_NAME = "enrollments"

COLUMNS = [
    "報名狀態",
    "聯繫狀態",
    "登記日期",
    "幼兒姓名",
    "家長稱呼",
    "電話",
    "幼兒生日",
    "預計入學資訊",
    "推薦人",
    "備註",
    "重要性"
]

REPORT_STATUS = ["新登記", "已入學", "候補", "不錄取"]
CONTACT_STATUS = ["未聯繫", "已聯繫", "已參觀", "無回應"]
IMPORTANCE = ["高", "中", "低"]

# =========================
# Google Sheets 連線
# =========================
@st.cache_resource
def get_client():
    import gspread
    from google.oauth2.service_account import Credentials
    sa = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(sa, scopes=scopes)
    return gspread.authorize(creds)

def open_ws():
    return get_client().open_by_url(SPREADSHEET_URL).worksheet(WORKSHEET_NAME)

def read_df():
    ws = open_ws()
    data = ws.get_all_values()
    if not data:
        return pd.DataFrame(columns=COLUMNS)
    df = pd.DataFrame(data[1:], columns=data[0])
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[COLUMNS]

def append_row(row):
    ws = open_ws()
    ws.append_row([row[c] for c in COLUMNS], value_input_option="USER_ENTERED")

def update_cell(row_idx, col_name, value):
    ws = open_ws()
    col_idx = COLUMNS.index(col_name) + 1
    ws.update_cell(row_idx + 2, col_idx, value)

# =========================
# 工具
# =========================
def normalize_phone(s):
    return re.sub(r"[^\d]", "", s or "")

# =========================
# Tabs
# =========================
tab1, tab2 = st.tabs(["📝 新生登記", "🗂️ 後台管理"])

# =========================
# Tab 1：新生登記（防重複）
# =========================
with tab1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 新生登記表單")
    st.markdown("</div>", unsafe_allow_html=True)

    df = read_df()

    with st.form("enroll_form", clear_on_submit=True):
        child = st.text_input("幼兒姓名 *")
        parent = st.text_input("家長稱呼 *")
        phone = st.text_input("電話 *", placeholder="0912345678")
        birth = st.date_input("幼兒生日 *", value=date(2022, 1, 1))
        enroll_info = st.text_input("預計入學資訊", placeholder="例如：114學年度小班")
        ref = st.text_input("推薦人（選填）")
        note = st.text_area("備註（選填）")

        submitted = st.form_submit_button("送出登記")

    if submitted:
        phone_clean = normalize_phone(phone)
        if phone_clean in df["電話"].astype(str).values:
            st.warning("⚠️ 此電話已有登記紀錄，請勿重複填寫。")
        else:
            row = {
                "報名狀態": "新登記",
                "聯繫狀態": "未聯繫",
                "登記日期": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "幼兒姓名": child.strip(),
                "家長稱呼": parent.strip(),
                "電話": phone_clean,
                "幼兒生日": str(birth),
                "預計入學資訊": enroll_info.strip(),
                "推薦人": ref.strip(),
                "備註": note.strip(),
                "重要性": "中"
            }
            append_row(row)
            st.success("✅ 登記完成，資料已送出！")

# =========================
# Tab 2：後台管理（狀態＋重要性）
# =========================
with tab2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 後台名單管理")
    st.markdown("</div>", unsafe_allow_html=True)

    df = read_df()
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("#### ✏️ 更新狀態 / 重要性")
    selected = st.selectbox("選擇幼兒", df["幼兒姓名"])
    new_report = st.selectbox("報名狀態", REPORT_STATUS)
    new_contact = st.selectbox("聯繫狀態", CONTACT_STATUS)
    new_imp = st.selectbox("重要性", IMPORTANCE)

    if st.button("更新資料"):
        idx = df[df["幼兒姓名"] == selected].index[0]
        update_cell(idx, "報名狀態", new_report)
        update_cell(idx, "聯繫狀態", new_contact)
        update_cell(idx, "重要性", new_imp)
        st.success("✅ 資料已更新，請重新整理")
