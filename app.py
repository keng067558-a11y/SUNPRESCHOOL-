import streamlit as st
import pandas as pd
from datetime import date, datetime
import re
import json

# =========================
# 0) 基本設定
# =========================
st.set_page_config(
    page_title="小太陽｜新生登記管理系統",
    page_icon="📝",
    layout="wide"
)

# =========================
# 1) Apple-style UI
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
.block-container{ max-width:1200px; padding-top:1.2rem; padding-bottom:2rem; }
.apple-header{
  background:linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,255,255,.60));
  border:1px solid var(--line);
  box-shadow:var(--shadow);
  border-radius:var(--r);
  padding:18px 20px;
  margin-bottom:16px;
}
.apple-title{ font-size:1.55rem; font-weight:900; letter-spacing:-0.02em; margin:0; }
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
  <div class="apple-title">📝 小太陽｜新生登記管理系統 <span class="badge">Excel 欄位同步</span></div>
  <div class="apple-sub">新生登記 ➜ 防重複（電話） ➜ 後台管理（報名狀態 / 聯繫狀態 / 重要性）</div>
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

def ensure_header_exact(ws) -> str:
    """
    讓 Google Sheet 第 1 列表頭「完全等於」你指定的 COLUMNS（含順序）。
    不會刪掉舊資料列，但若舊資料是用不同表頭寫入，顯示會以目前欄位為主。
    """
    header = get_sheet_header(ws)
    if header == COLUMNS:
        return "表頭已完全一致（含順序）✅"
    ws.update("A1", [COLUMNS])
    return "已將表頭同步為最新欄位（含順序）✅"

def read_df() -> pd.DataFrame:
    ws = open_ws()
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=COLUMNS)

    header = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=header)

    # 對齊到指定欄位＆順序
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[COLUMNS].copy()
    return df

def append_row(row: dict):
    ws = open_ws()
    # 寫入前保證表頭一致
    ensure_header_exact(ws)
    ws.append_row([row.get(c, "") for c in COLUMNS], value_input_option="USER_ENTERED")

def update_cell_by_row_index(row_index_in_df: int, col_name: str, value: str):
    """
    row_index_in_df: DataFrame 的 index（從 0 開始）
    Google Sheet 的實際列 = row_index_in_df + 2（因為第 1 列是表頭）
    """
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
# 5) Tabs
# =========================
tab1, tab2, tab3 = st.tabs(["📝 新生登記", "🗂️ 後台管理", "⚙️ 表頭同步"])

# =========================
# Tab 1：新生登記（防重複：電話）
# =========================
with tab1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 新生登記表單（電話防重複）")
    st.markdown('<div class="small">同一支「電話」已登記過，系統會提醒並阻止重複新增。</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        df = read_df()
    except Exception as e:
        st.error("❌ 讀取試算表失敗（請確認 Secrets 與分享權限）")
        st.code(str(e))
        st.stop()

    with st.form("enroll_form", clear_on_submit=True):
        colA, colB = st.columns([1.2, 1])
        with colA:
            child_name = st.text_input("幼兒姓名 *", placeholder="例如：王小明")
        with colB:
            parent_title = st.text_input("家長稱呼 *", placeholder="例如：王爸爸 / 王媽媽")

        colC, colD = st.columns([1, 1])
        with colC:
            phone = st.text_input("電話 *", placeholder="例如：0912345678")
        with colD:
            child_bday = st.date_input("幼兒生日 *", value=date(2022, 1, 1))

        enroll_info = st.text_input("預計入學資訊（選填）", placeholder="例如：114學年度小班 / 2026-09")
        referrer = st.text_input("推薦人（選填）", placeholder="例如：某某家長 / 老師 / 朋友")
        notes = st.text_area("備註（選填）", placeholder="例如：過敏、想約參觀、是否需補助…")

        submitted = st.form_submit_button("✅ 送出登記", use_container_width=True)

    if submitted:
        phone_clean = normalize_phone(phone)

        errors = []
        if not child_name.strip():
            errors.append("請填寫「幼兒姓名」")
        if not parent_title.strip():
            errors.append("請填寫「家長稱呼」")
        if len(phone_clean) < 9:
            errors.append("請填寫正確電話（至少 9 碼）")

        if errors:
            st.error("⚠️ 請修正：\n- " + "\n- ".join(errors))
        else:
            # 防重複：電話
            if phone_clean in df["電話"].astype(str).values:
                st.warning("⚠️ 此電話已有登記紀錄，請勿重複填寫。若要更新狀態請到「後台管理」。")
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

                try:
                    append_row(row)
                    st.success("✅ 登記完成！資料已寫入試算表。")
                except Exception as e:
                    st.error("❌ 寫入失敗（通常是試算表未分享 service account 編輯權限）")
                    st.code(str(e))

# =========================
# Tab 2：後台管理（更新：報名狀態／聯繫狀態／重要性）
# =========================
with tab2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 後台管理（更新狀態／重要性）")
    st.markdown('<div class="small">建議你先到「⚙️ 表頭同步」按一次，確保 Excel 表頭與順序完全一致。</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        df = read_df()
    except Exception as e:
        st.error("❌ 讀取失敗")
        st.code(str(e))
        st.stop()

    # 顯示列表（完全用你的欄位順序）
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("#### 🔎 篩選（可選）")
    f1, f2, f3, f4 = st.columns([1, 1, 1, 1.2])
    with f1:
        f_report = st.selectbox("報名狀態", ["全部"] + REPORT_STATUS)
    with f2:
        f_contact = st.selectbox("聯繫狀態", ["全部"] + CONTACT_STATUS)
    with f3:
        f_imp = st.selectbox("重要性", ["全部"] + IMPORTANCE)
    with f4:
        kw = st.text_input("關鍵字（幼兒/家長/電話/備註）", placeholder="輸入關鍵字…")

    filtered = df.copy()
    if len(filtered):
        if f_report != "全部":
            filtered = filtered[filtered["報名狀態"] == f_report]
        if f_contact != "全部":
            filtered = filtered[filtered["聯繫狀態"] == f_contact]
        if f_imp != "全部":
            filtered = filtered[filtered["重要性"] == f_imp]
        if kw.strip():
            k = kw.strip()
            filtered = filtered[
                filtered["幼兒姓名"].astype(str).str.contains(k, na=False) |
                filtered["家長稱呼"].astype(str).str.contains(k, na=False) |
                filtered["電話"].astype(str).str.contains(k, na=False) |
                filtered["備註"].astype(str).str.contains(k, na=False) |
                filtered["推薦人"].astype(str).str.contains(k, na=False) |
                filtered["預計入學資訊"].astype(str).str.contains(k, na=False)
            ]

    st.markdown("#### 📌 篩選結果")
    st.metric("筆數", len(filtered))
    st.dataframe(filtered, use_container_width=True, hide_index=True)

    st.markdown("#### ✏️ 更新單筆（用「電話」定位）")
    if len(df) == 0:
        st.info("目前還沒有資料。")
    else:
        # 用電話當唯一鍵（避免同名問題）
        phone_list = df["電話"].astype(str).tolist()
        target_phone = st.selectbox("選擇要更新的電話", phone_list)

        # 找到那筆 row
        row_idx = df.index[df["電話"].astype(str) == str(target_phone)].tolist()[0]

        cur_report = df.loc[row_idx, "報名狀態"] if df.loc[row_idx, "報名狀態"] else "新登記"
        cur_contact = df.loc[row_idx, "聯繫狀態"] if df.loc[row_idx, "聯繫狀態"] else "未聯繫"
        cur_imp = df.loc[row_idx, "重要性"] if df.loc[row_idx, "重要性"] else "中"

        u1, u2, u3 = st.columns(3)
        with u1:
            new_report = st.selectbox("報名狀態（更新）", REPORT_STATUS, index=REPORT_STATUS.index(cur_report) if cur_report in REPORT_STATUS else 0)
        with u2:
            new_contact = st.selectbox("聯繫狀態（更新）", CONTACT_STATUS, index=CONTACT_STATUS.index(cur_contact) if cur_contact in CONTACT_STATUS else 0)
        with u3:
            new_imp = st.selectbox("重要性（更新）", IMPORTANCE, index=IMPORTANCE.index(cur_imp) if cur_imp in IMPORTANCE else 1)

        if st.button("✅ 寫入更新", use_container_width=True):
            try:
                update_cell_by_row_index(row_idx, "報名狀態", new_report)
                update_cell_by_row_index(row_idx, "聯繫狀態", new_contact)
                update_cell_by_row_index(row_idx, "重要性", new_imp)
                st.success("✅ 已更新完成！")
                st.rerun()
            except Exception as e:
                st.error("❌ 更新失敗")
                st.code(str(e))

    st.markdown("#### 📥 匯出")
    csv_bytes = filtered.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("下載篩選結果 CSV", data=csv_bytes, file_name="新生登記_篩選結果.csv", mime="text/csv")

# =========================
# Tab 3：表頭同步（讓 Excel 跟系統 100% 一致）
# =========================
with tab3:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### ⚙️ 表頭同步（讓 Excel 變成你指定的欄位＆順序）")
    st.markdown(
        '<div class="small">按下去會把 Google Sheet 的第 1 列改成：<br>'
        '報名狀態｜聯繫狀態｜登記日期｜幼兒姓名｜家長稱呼｜電話｜幼兒生日｜預計入學資訊｜推薦人｜備註｜重要性</div>',
        unsafe_allow_html=True
    )

    try:
        ws = open_ws()
        current = get_sheet_header(ws)
        st.markdown("#### 目前 Excel 第 1 列表頭：")
        st.write(current if current else "（目前是空的）")

        if st.button("✅ 一鍵同步表頭（含順序）", use_container_width=True):
            msg = ensure_header_exact(ws)
            st.success(msg)
            st.info("回到「後台管理」重新整理即可。")

    except Exception as e:
        st.error("❌ 無法讀取/同步表頭")
        st.code(str(e))

    st.markdown("</div>", unsafe_allow_html=True)
