import streamlit as st
import pandas as pd
from datetime import date
import re
import json

# =========================
# 基本設定
# =========================
st.set_page_config(
    page_title="小太陽｜新生報名系統",
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
.block-container{ max-width:1100px; padding-top:1.4rem; }
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

# =========================
# Google Sheet 設定
# =========================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Pz7z9CdU8MODTdXbckXCnI0NpjXquZDcZCC-DTOen3o/edit"
WORKSHEET_NAME = "enrollments"

COLUMNS = [
    "孩子姓名",
    "性別",
    "出生年月日",
    "欲就讀班別",
    "家長姓名",
    "與幼兒關係",
    "聯絡電話",
    "備註",
    "狀態"
]

STATUS_OPTIONS = ["新報名", "已聯絡", "已參觀", "已入學", "候補"]

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

def update_status(row_idx, new_status):
    ws = open_ws()
    status_col = COLUMNS.index("狀態") + 1
    ws.update_cell(row_idx + 2, status_col, new_status)

# =========================
# 工具
# =========================
def normalize_phone(s):
    return re.sub(r"[^\d]", "", s or "")

# =========================
# Tabs
# =========================
tab1, tab2 = st.tabs(["📝 新生報名", "🗂️ 後台管理"])

# =========================
# Tab 1：新生報名（防重複）
# =========================
with tab1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 新生報名表單")
    st.markdown("</div>", unsafe_allow_html=True)

    df = read_df()

    with st.form("enroll_form", clear_on_submit=True):
        child = st.text_input("孩子姓名 *")
        gender = st.selectbox("性別", ["男", "女", "不方便透露"])
        birth = st.date_input("出生年月日 *", value=date(2022, 1, 1))
        cls = st.selectbox("欲就讀班別 *", ["幼幼班", "小班", "中班", "大班", "不確定"])
        parent = st.text_input("家長姓名 *")
        relation = st.selectbox("與幼兒關係", ["父親", "母親", "監護人", "祖父母", "其他"])
        phone = st.text_input("聯絡電話 *")
        note = st.text_area("備註")

        submitted = st.form_submit_button("送出報名")

    if submitted:
        phone_clean = normalize_phone(phone)
        if phone_clean in df["聯絡電話"].astype(str).values:
            st.warning("⚠️ 此聯絡電話已有報名紀錄，請勿重複填寫。")
        else:
            row = {
                "孩子姓名": child.strip(),
                "性別": gender,
                "出生年月日": str(birth),
                "欲就讀班別": cls,
                "家長姓名": parent.strip(),
                "與幼兒關係": relation,
                "聯絡電話": phone_clean,
                "備註": note.strip(),
                "狀態": "新報名"
            }
            append_row(row)
            st.success("✅ 報名完成，已成功送出！")

# =========================
# Tab 2：後台狀態管理
# =========================
with tab2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 後台報名名單（可直接改狀態）")
    st.markdown("</div>", unsafe_allow_html=True)

    df = read_df()
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("#### 狀態更新")
    selected = st.selectbox("選擇孩子", df["孩子姓名"])
    new_status = st.selectbox("更新為", STATUS_OPTIONS)

    if st.button("更新狀態"):
        idx = df[df["孩子姓名"] == selected].index[0]
        update_status(idx, new_status)
        st.success("✅ 狀態已更新，請重新整理頁面")
