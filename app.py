import streamlit as st
import pandas as pd
from datetime import datetime, date
import re
import json

# =========================
# Apple-style UI
# =========================
st.set_page_config(page_title="小太陽｜新生報名系統", page_icon="📝", layout="wide")

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
.block-container{ max-width:1100px; padding-top:1.4rem; padding-bottom:2rem; }
.apple-header{
  background:linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,255,255,.60));
  border:1px solid var(--line);
  box-shadow:var(--shadow);
  border-radius:var(--r);
  padding:18px 20px;
  margin-bottom:16px;
}
.apple-title{ font-size:1.6rem; font-weight:900; letter-spacing:-0.02em; margin:0; }
.apple-sub{ color:var(--muted); margin-top:6px; font-size:.95rem; line-height:1.35; }
.apple-card{
  background:var(--card);
  border:1px solid var(--line);
  border-radius:var(--r);
  box-shadow:var(--shadow);
  padding:18px 18px;
  margin-bottom:16px;
}
.small{ color:var(--muted); font-size:.9rem; }
.badge{
  display:inline-block; padding:4px 10px; border-radius:999px; font-size:.85rem;
  border:1px solid var(--line); background:rgba(0,0,0,.03); margin-left:8px;
}
.stButton>button{
  border-radius:14px; padding:10px 16px; background:#111; color:#fff; font-weight:800;
  border:1px solid var(--line);
}
.stButton>button:hover{ opacity:.92; }
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input,
div[data-testid="stSelectbox"] > div,
div[data-testid="stNumberInput"] input{ border-radius:14px !important; }
hr{ border:none; border-top:1px solid var(--line); margin:12px 0 18px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="apple-header">
  <div class="apple-title">📝 小太陽｜新生報名系統 <span class="badge">中文欄位</span></div>
  <div class="apple-sub">家長填表 → 立即寫入 Google 試算表（enrollments）→ 後台中文列表可查詢</div>
</div>
""", unsafe_allow_html=True)

# =========================
# Google Sheet 設定
# =========================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Pz7z9CdU8MODTdXbckXCnI0NpjXquZDcZCC-DTOen3o/edit?usp=sharing"
WORKSHEET_NAME = "enrollments"

# 你目前最終保留的中文欄位
COLUMNS = [
    "孩子姓名",
    "性別",
    "出生年月日",
    "欲就讀班別",
    "家長姓名",
    "與幼兒關係",
    "聯絡電話",
    "備註",
]

# =========================
# Google Sheets 連線（gspread）
# =========================
@st.cache_resource
def get_gspread_client():
    import gspread
    from google.oauth2.service_account import Credentials

    if "GOOGLE_SERVICE_ACCOUNT_JSON" not in st.secrets:
        raise RuntimeError("找不到 GOOGLE_SERVICE_ACCOUNT_JSON。請到 Streamlit Secrets 貼上 service account JSON。")

    sa = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sa_info = json.loads(sa) if isinstance(sa, str) else dict(sa)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)

def open_worksheet():
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    return sh.worksheet(WORKSHEET_NAME)

def get_header(ws) -> list:
    values = ws.get_all_values()
    if not values:
        return []
    return values[0]

def ensure_header_is_chinese(ws):
    """
    如果表頭不是 COLUMNS，就把 A1 起整列改成 COLUMNS。
    不動既有資料列（但如果之前英文表頭下的資料列是不同欄數，顯示會以你現在欄位為主）。
    """
    header = get_header(ws)
    if header == COLUMNS:
        return True, "表頭已是中文（正確）"
    # 如果 sheet 是空的或表頭不符合，就寫入中文表頭
    ws.update("A1", [COLUMNS])
    return True, "已將表頭初始化/修正為中文"

def read_sheet_df() -> pd.DataFrame:
    ws = open_worksheet()
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=COLUMNS)

    header = values[0]
    rows = values[1:]

    # 若表頭不是中文欄位，仍先用現有 header 讀，再做欄位對齊
    df = pd.DataFrame(rows, columns=header if header else list(range(len(rows[0]))))

    # 對齊到中文欄位（缺的補空字串）
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[COLUMNS].copy()

    # 基本清理
    df["孩子姓名"] = df["孩子姓名"].astype(str)
    df["家長姓名"] = df["家長姓名"].astype(str)
    df["聯絡電話"] = df["聯絡電話"].astype(str)
    return df

def append_row(row: dict):
    ws = open_worksheet()
    # 寫入前先確保表頭是中文（避免又被英文表頭影響）
    ensure_header_is_chinese(ws)
    ws.append_row([row.get(c, "") for c in COLUMNS], value_input_option="USER_ENTERED")

# =========================
# 工具
# =========================
def normalize_phone(s: str) -> str:
    s = (s or "").strip()
    return re.sub(r"[^\d]", "", s)

# =========================
# Tabs
# =========================
tab1, tab2, tab3 = st.tabs(["📝 新生報名", "🗂️ 後台列表", "⚙️ 表頭修正"])

# =========================
# Tab 1：新生報名
# =========================
with tab1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 新生報名表單（寫入 Google 試算表）")
    st.markdown('<div class="small">欄位會對應你目前保留的 8 個中文欄位。</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("enroll_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            child_name = st.text_input("孩子姓名 *", placeholder="例如：王小明")
        with c2:
            gender = st.selectbox("性別", ["男", "女", "不方便透露"], index=2)

        birth_date = st.date_input("出生年月日 *", value=date(2022, 1, 1))

        class_choice = st.selectbox("欲就讀班別 *", ["幼幼班", "小班", "中班", "大班", "不確定"])

        c3, c4 = st.columns(2)
        with c3:
            parent_name = st.text_input("家長姓名 *", placeholder="例如：王爸爸")
        with c4:
            relation = st.selectbox("與幼兒關係", ["父親", "母親", "監護人", "祖父母", "其他"])

        phone = st.text_input("聯絡電話 *", placeholder="例如：0912345678")
        notes = st.text_area("備註（選填）", placeholder="例如：過敏、想約參觀時間、是否需要補助...")

        submitted = st.form_submit_button("✅ 送出報名", use_container_width=True)

    if submitted:
        errors = []
        if not child_name.strip():
            errors.append("請填寫孩子姓名")
        if not parent_name.strip():
            errors.append("請填寫家長姓名")
        phone_clean = normalize_phone(phone)
        if len(phone_clean) < 9:
            errors.append("請填寫正確的聯絡電話（至少 9 碼）")

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
                "備註": (notes or "").strip(),
            }
            try:
                append_row(row)
                st.success("✅ 報名已送出，感謝您的填寫！")
                st.info("你可以到「後台列表」立即看到剛剛新增的資料。")
            except Exception as e:
                st.error("❌ 寫入失敗（通常是：試算表沒分享給 service account 編輯權限 / Secrets 錯）")
                st.code(str(e))

# =========================
# Tab 2：後台列表（中文）
# =========================
with tab2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 後台列表（中文欄位）")
    st.markdown('<div class="small">如果你之前表頭是英文，請到「⚙️ 表頭修正」按一下初始化，列表就會全部中文。</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        df = read_sheet_df()
        st.metric("目前筆數", len(df))
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 下載 CSV", data=csv_bytes, file_name="新生報名資料.csv", mime="text/csv")
    except Exception as e:
        st.error("❌ 讀取失敗")
        st.code(str(e))

# =========================
# Tab 3：表頭修正（中文化一鍵完成）
# =========================
with tab3:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### ⚙️ 表頭修正（把英文表頭變中文）")
    st.markdown("""
<div class="small">
如果你說「列表還是英文」，最常見就是 Google Sheet 的第 1 列表頭仍是英文。<br/>
按下面按鈕會把 <b>enrollments</b> 的第 1 列改成你目前的 8 個中文欄位：<br/>
<code>孩子姓名 / 性別 / 出生年月日 / 欲就讀班別 / 家長姓名 / 與幼兒關係 / 聯絡電話 / 備註</code>
</div>
""", unsafe_allow_html=True)

    if st.button("✅ 一鍵初始化/修正表頭為中文", use_container_width=True):
        try:
            ws = open_worksheet()
            ok, msg = ensure_header_is_chinese(ws)
            if ok:
                st.success(f"✅ {msg}")
                st.info("回到「後台列表」重新整理，就會看到中文欄位。")
        except Exception as e:
            st.error("❌ 表頭修正失敗")
            st.code(str(e))

    try:
        ws = open_worksheet()
        header_now = get_header(ws)
        st.markdown("#### 目前 Google Sheet 第 1 列表頭：")
        st.write(header_now if header_now else "（目前是空的）")
    except Exception as e:
        st.error("❌ 無法讀取目前表頭")
        st.code(str(e))

    st.markdown("</div>", unsafe_allow_html=True)
