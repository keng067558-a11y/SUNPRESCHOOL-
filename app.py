import streamlit as st
import pandas as pd
from datetime import date, datetime
import re
import json

# =========================
# 0) 基本設定
# =========================
st.set_page_config(
    page_title="小太陽｜新生報名",
    page_icon="📝",
    layout="wide"
)

# =========================
# 1) 極簡 Apple 風格 UI
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
.block-container{ max-width:1050px; padding-top:1.1rem; padding-bottom:2rem; }
.topbar{
  display:flex; align-items:center; justify-content:space-between;
  background:rgba(255,255,255,.85);
  border:1px solid var(--line);
  box-shadow:var(--shadow);
  border-radius:var(--r);
  padding:14px 18px;
  margin-bottom:14px;
}
.brand{
  display:flex; align-items:center; gap:10px;
}
.logo{
  width:36px; height:36px; border-radius:12px;
  display:flex; align-items:center; justify-content:center;
  background:rgba(0,0,0,.04); border:1px solid var(--line);
  font-size:18px;
}
.title{
  font-size:1.35rem; font-weight:900; letter-spacing:-0.02em; margin:0;
}
.card{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:var(--r);
  box-shadow:var(--shadow);
  padding:18px;
  margin-bottom:14px;
}
.small{ color:var(--muted); font-size:.92rem; }
.stButton>button{
  border-radius:14px; padding:10px 16px; background:#111; color:#fff; font-weight:800;
  border:1px solid var(--line);
}
.stButton>button:hover{ opacity:.92; }
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input,
div[data-testid="stSelectbox"] > div{ border-radius:14px !important; }
hr{ border:none; border-top:1px solid var(--line); margin:10px 0 14px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="topbar">
  <div class="brand">
    <div class="logo">📝</div>
    <div>
      <div class="title">小太陽｜新生報名</div>
      <div class="small">填寫資料，送出即可</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================
# 2) Google Sheet 設定（你的正確欄位＆順序）
# =========================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Pz7z9CdU8MODTdXbckXCnI0NpjXquZDcZCC-DTOen3o/edit?usp=sharing"
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
    "重要性",
]

REPORT_STATUS = ["新登記", "已入學", "候補", "不錄取"]
CONTACT_STATUS = ["未聯繫", "已聯繫", "已參觀", "無回應"]
IMPORTANCE = ["高", "中", "低"]

DEFAULT_ROW = {
    "報名狀態": "新登記",
    "聯繫狀態": "未聯繫",
    "重要性": "中",
}

# =========================
# 3) Google Sheets（gspread）
# =========================
@st.cache_resource
def get_gspread_client():
    import gspread
    from google.oauth2.service_account import Credentials

    if "GOOGLE_SERVICE_ACCOUNT_JSON" not in st.secrets:
        raise RuntimeError("找不到 Secrets：GOOGLE_SERVICE_ACCOUNT_JSON")

    sa = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(sa) if isinstance(sa, str) else dict(sa)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)

def open_ws():
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    return sh.worksheet(WORKSHEET_NAME)

def get_sheet_header(ws) -> list:
    values = ws.get_all_values()
    if not values:
        return []
    return values[0]

def ensure_header_exact(ws):
    # 靜默同步表頭（不顯示任何UI字樣）
    header = get_sheet_header(ws)
    if header != COLUMNS:
        ws.update("A1", [COLUMNS])

def read_df() -> pd.DataFrame:
    ws = open_ws()
    ensure_header_exact(ws)

    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=COLUMNS)

    header = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=header)

    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[COLUMNS].copy()

def append_row(row: dict):
    ws = open_ws()
    ensure_header_exact(ws)
    ws.append_row([row.get(c, "") for c in COLUMNS], value_input_option="USER_ENTERED")

def update_cell_by_row_index(row_index_in_df: int, col_name: str, value: str):
    ws = open_ws()
    ensure_header_exact(ws)
    col_idx = COLUMNS.index(col_name) + 1
    ws.update_cell(row_index_in_df + 2, col_idx, value)

# =========================
# 4) 工具
# =========================
def normalize_phone(s: str) -> str:
    return re.sub(r"[^\d]", "", (s or "").strip())

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# =========================
# 5) 兩個頁面（極簡）
# =========================
tab_form, tab_list = st.tabs(["表單", "名單"])

# =========================
# Tab 1：表單（不做電話防重複）
# =========================
with tab_form:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 新生報名表單")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("enroll_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            child_name = st.text_input("幼兒姓名 *", placeholder="例如：王小明")
        with c2:
            parent_title = st.text_input("家長稱呼 *", placeholder="例如：王爸爸／王媽媽")

        c3, c4 = st.columns(2)
        with c3:
            phone = st.text_input("電話 *", pl*_
