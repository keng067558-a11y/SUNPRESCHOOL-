import streamlit as st
import pandas as pd
from datetime import date
import re
import json

# =========================
# Apple-style UI
# =========================
st.set_page_config(
    page_title="小太陽｜新生報名系統",
    page_icon="📝",
    layout="wide"
)

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
.block-container{ max-width:900px; padding-top:1.6rem; }
.apple-card{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:var(--r);
  box-shadow:var(--shadow);
  padding:20px;
  margin-bottom:18px;
}
.apple-title{
  font-size:1.6rem;
  font-weight:900;
  letter-spacing:-0.02em;
}
.apple-sub{
  color:var(--muted);
  margin-top:6px;
}
.stButton>button{
  border-radius:14px;
  padding:10px 16px;
  background:#111;
  color:#fff;
  font-weight:800;
}
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input,
div[data-testid="stSelectbox"] > div{
  border-radius:14px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="apple-card">
  <div class="apple-title">📝 小太陽｜新生報名系統</div>
  <div class="apple-sub">請家長填寫以下資料，我們將盡快與您聯繫。</div>
</div>
""", unsafe_allow_html=True)

# =========================
# Google Sheet 設定
# =========================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Pz7z9CdU8MODTdXbckXCnI0NpjXquZDcZCC-DTOen3o/edit"
WORKSHEET_NAME = "enrollments"

# 你目前 Excel 的最終欄位（中文）
COLUMNS = [
    "孩子姓名",
    "性別",
    "出生年月日",
    "欲就讀班別",
    "家長姓名",
    "與幼兒關係",
    "聯絡電話",
    "備註"
]

# =========================
# Google Sheets 連線（gspread）
# =========================
@st.cache_resource
def get_gspread_client():
    import gspread
    from google.oauth2.service_account import Credentials

    if "GOOGLE_SERVICE_ACCOUNT_JSON" not in st.secrets:
        raise RuntimeError("找不到 GOOGLE_SERVICE_ACCOUNT_JSON（請到 Streamlit Secrets 設定）")

    sa = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(sa) if isinstance(sa, str) else dict(sa)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)

def open_worksheet():
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    return sh.worksheet(WORKSHEET_NAME)

def read_sheet() -> pd.DataFrame:
    ws = open_worksheet()
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=COLUMNS)
    header = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=header)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[COLUMNS]

def write_row(row: dict):
    ws = open_worksheet()
    ws.append_row([row[c] for c in COLUMNS], value_input_option="USER_ENTERED")

# =========================
# 工具
# =========================
def normalize_phone(s: str) -> str:
    s = (s or "").strip()
    return re.sub(r"[^\d]", "", s)

# =========================
# 表單（新生報名）
# =========================
st.markdown('<div class="apple-card">', unsafe_allow_html=True)
st.markdown("### 新生報名表單")

with st.form("enroll_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        child_name = st.text_input("孩子姓名 *")
    with c2:
        gender = st.selectbox("性別", ["男", "女", "不方便透露"])

    birth_date = st.date_input("出生年月日 *", value=date(2022, 1, 1))

    class_choice = st.selectbox("欲就讀班別 *", ["幼幼班", "小班", "中班", "大班", "不確定"])

    g1, g2 = st.columns(2)
    with g1:
        parent_name = st.text_input("家長姓名 *")
    with g2:
        relation = st.selectbox("與幼兒關係", ["父親", "母親", "監護人", "祖父母", "其他"])

    phone = st.text_input("聯絡電話 *", placeholder="例如：0912345678")

    notes = st.text_area("備註（選填）")

    submitted = st.form_submit_button("✅ 送出報名", use_container_width=True)

if submitted:
    errors = []
    if not child_name.strip():
        errors.append("請填寫孩子姓名")
    if not parent_name.strip():
        errors.append("請填寫家長姓名")
    phone_clean = normalize_phone(phone)
    if len(phone_clean) < 9:
        errors.append("請填寫正確的聯絡電話")

    if errors:
        st.error("⚠️ 請修正以下問題：\n- " + "\n- ".join(errors))
    else:
        row = {
            "孩子姓名": child_name.strip(),
            "性別": gender,
            "出生年月日": str(birth_date),
            "欲就讀班別": class_choice,
            "家長姓名": parent_name.strip(),
            "與幼兒關係": relation,
            "聯絡電話": phone_clean,
            "備註": notes.strip()
        }
        try:
            write_row(row)
            st.success("✅ 報名已送出，感謝您的填寫！")
        except Exception as e:
            st.error("❌ 寫入 Google 試算表失敗（請確認權限與 Secrets 設定）")
            st.code(str(e))

st.markdown("</div>", unsafe_allow_html=True)
