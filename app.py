import streamlit as st
import pandas as pd
from datetime import date, datetime
import re
import json

# =========================
# 0) 基本設定
# =========================
st.set_page_config(
    page_title="小太陽｜幼兒園管理系統",
    page_icon="🏫",
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
.block-container{ max-width:1150px; padding-top:1.1rem; padding-bottom:2rem; }
.topbar{
  display:flex; align-items:center; justify-content:space-between;
  background:rgba(255,255,255,.85);
  border:1px solid var(--line);
  box-shadow:var(--shadow);
  border-radius:var(--r);
  padding:14px 18px;
  margin-bottom:14px;
}
.brand{ display:flex; align-items:center; gap:10px; }
.logo{
  width:36px; height:36px; border-radius:12px;
  display:flex; align-items:center; justify-content:center;
  background:rgba(0,0,0,.04); border:1px solid var(--line);
  font-size:18px;
}
.title{ font-size:1.35rem; font-weight:900; letter-spacing:-0.02em; margin:0; }
.small{ color:var(--muted); font-size:.92rem; }
.card{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:var(--r);
  box-shadow:var(--shadow);
  padding:18px;
  margin-bottom:14px;
}
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
    <div class="logo">🏫</div>
    <div>
      <div class="title">小太陽｜幼兒園管理系統</div>
      <div class="small">簡約、直觀</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================
# 2) Google Sheet 設定（新增：預計就讀）
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
    "預計就讀",   # ✅ 新增欄位（確認就讀的人）
]

REPORT_STATUS = ["新登記", "已入學", "候補", "不錄取"]
CONTACT_STATUS = ["未聯繫", "已聯繫", "已參觀", "無回應"]
IMPORTANCE = ["高", "中", "低"]
WILL_ENROLL = ["未確認", "確認就讀"]  # 你要的「確認就讀的人」

DEFAULT_ROW = {
    "報名狀態": "新登記",
    "聯繫狀態": "未聯繫",
    "重要性": "中",
    "預計就讀": "未確認"
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
# 5) 管理系統分頁（你要的：新生登記）
# =========================
tab_enroll, tab_placeholder = st.tabs(["新生登記", "（其他模組）"])

# =========================
# 新生登記：表單 / 名單
# =========================
with tab_enroll:
    t1, t2 = st.tabs(["表單", "名單"])

    # ---------- 表單 ----------
    with t1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 新生登記")
        st.markdown("</div>", unsafe_allow_html=True)

        with st.form("enroll_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                child_name = st.text_input("幼兒姓名 *", placeholder="例如：王小明")
            with c2:
                parent_title = st.text_input("家長稱呼 *", placeholder="例如：王爸爸／王媽媽")

            c3, c4 = st.columns(2)
            with c3:
                phone = st.text_input("電話 *", placeholder="例如：0912345678")
            with c4:
                child_bday = st.date_input("幼兒生日 *", value=date(2022, 1, 1))

            enroll_info = st.text_input("預計入學資訊", placeholder="例如：114學年度小班／2026-09")
            referrer = st.text_input("推薦人", placeholder="選填")
            notes = st.text_area("備註", placeholder="選填")

            # ✅ 新增：預計就讀（確認就讀的人）
            will_enroll = st.selectbox("預計就讀", WILL_ENROLL, index=0)

            submitted = st.form_submit_button("送出", use_container_width=True)

        if submitted:
            phone_clean = normalize_phone(phone)
            errors = []
            if not child_name.strip():
                errors.append("請填寫幼兒姓名")
            if not parent_title.strip():
                errors.append("請填寫家長稱呼")
            if len(phone_clean) < 9:
                errors.append("請填寫正確電話")

            if errors:
                st.error("請修正：\n- " + "\n- ".join(errors))
            else:
                row = {c: "" for c in COLUMNS}
                row.update(DEFAULT_ROW)

                row["登記日期"] = now_str()
                row["幼兒姓名"] = child_name.strip()
                row["家長稱呼"] = parent_title.strip()
                row["電話"] = phone_clean
                row["幼兒生日"] = str(child_bday)
                row["預計入學資訊"] = (enroll_info or "").strip()
                row["推薦人"] = (referrer or "").strip()
                row["備註"] = (notes or "").strip()
                row["預計就讀"] = will_enroll

                try:
                    append_row(row)
                    st.success("已送出")
                except Exception as e:
                    st.error("寫入失敗")
                    st.code(str(e))

    # ---------- 名單 ----------
    with t2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 名單")
        st.markdown("</div>", unsafe_allow_html=True)

        try:
            df = read_df()
        except Exception as e:
            st.error("讀取失敗")
            st.code(str(e))
            st.stop()

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 更新")
        if len(df) == 0:
            st.info("目前沒有資料")
        else:
            phone_list = df["電話"].astype(str).tolist()
            target_phone = st.selectbox("選擇電話", phone_list)

            row_idx = df.index[df["電話"].astype(str) == str(target_phone)].tolist()[0]

            cur_report = df.loc[row_idx, "報名狀態"] or "新登記"
            cur_contact = df.loc[row_idx, "聯繫狀態"] or "未聯繫"
            cur_imp = df.loc[row_idx, "重要性"] or "中"
            cur_will = df.loc[row_idx, "預計就讀"] or "未確認"

            a, b, c, d = st.columns(4)
            with a:
                new_report = st.selectbox("報名狀態", REPORT_STATUS,
                                          index=REPORT_STATUS.index(cur_report) if cur_report in REPORT_STATUS else 0)
            with b:
                new_contact = st.selectbox("聯繫狀態", CONTACT_STATUS,
                                           index=CONTACT_STATUS.index(cur_contact) if cur_contact in CONTACT_STATUS else 0)
            with c:
                new_imp = st.selectbox("重要性", IMPORTANCE,
                                       index=IMPORTANCE.index(cur_imp) if cur_imp in IMPORTANCE else 1)
            with d:
                new_will = st.selectbox("預計就讀", WILL_ENROLL,
                                        index=WILL_ENROLL.index(cur_will) if cur_will in WILL_ENROLL else 0)

            if st.button("儲存", use_container_width=True):
                try:
                    update_cell_by_row_index(row_idx, "報名狀態", new_report)
                    update_cell_by_row_index(row_idx, "聯繫狀態", new_contact)
                    update_cell_by_row_index(row_idx, "重要性", new_imp)
                    update_cell_by_row_index(row_idx, "預計就讀", new_will)
                    st.success("已更新")
                    st.rerun()
                except Exception as e:
                    st.error("更新失敗")
                    st.code(str(e))

with tab_placeholder:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 其他模組")
    st.markdown('<div class="small">之後你要加：在園生名單、收費、出缺勤、班級管理…都放這裡。</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
