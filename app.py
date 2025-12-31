import streamlit as st
import pandas as pd
from datetime import datetime, date
import re
import json

# =========================
# Apple-ish UI
# =========================
st.set_page_config(page_title="小太陽｜新生報名系統", page_icon="📝", layout="wide")

st.markdown("""
<style>
:root{
  --bg:#F5F5F7; --card:#fff; --text:#1D1D1F; --muted:#6E6E73;
  --line:rgba(0,0,0,.06); --shadow:0 10px 30px rgba(0,0,0,.08); --r:18px;
}
.stApp{ background:var(--bg); color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Segoe UI","Noto Sans TC","Microsoft JhengHei",sans-serif; }
.block-container{ padding-top:1.4rem; padding-bottom:2rem; max-width:1100px; }
.apple-header{ background:linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,255,255,.60));
  border:1px solid var(--line); box-shadow:var(--shadow); border-radius:var(--r);
  padding:18px 20px; margin-bottom:16px; }
.apple-title{ font-size:1.6rem; font-weight:900; margin:0; letter-spacing:-0.02em; }
.apple-sub{ color:var(--muted); margin-top:6px; font-size:.95rem; line-height:1.35; }
.apple-card{ background:var(--card); border:1px solid var(--line); border-radius:var(--r);
  box-shadow:var(--shadow); padding:16px 18px; margin-bottom:16px; }
.small{ color:var(--muted); font-size:.9rem; }
.badge{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:.85rem;
  border:1px solid var(--line); background:rgba(0,0,0,.03); margin-left:6px; }
.stButton>button{ border-radius:14px; padding:10px 14px; background:#111; color:#fff;
  border:1px solid var(--line); font-weight:800; }
.stButton>button:hover{ opacity:.92; }
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input,
div[data-testid="stSelectbox"] > div,
div[data-testid="stNumberInput"] input{ border-radius:14px !important; }
hr{ border:none; border-top:1px solid var(--line); margin:10px 0 18px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="apple-header">
  <div class="apple-title">📝 小太陽｜新生報名系統 <span class="badge">Google 試算表</span></div>
  <div class="apple-sub">家長填表 → 立即寫入 Google 試算表（enrollments）→ 後台查詢、更新狀態、匯出</div>
</div>
""", unsafe_allow_html=True)

# =========================
# 你的試算表設定（固定）
# =========================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Pz7z9CdU8MODTdXbckXCnI0NpjXquZDcZCC-DTOen3o/edit"
WORKSHEET_NAME = "enrollments"

COLUMNS = [
    "id","timestamp",
    "student_name","gender","birth_date",
    "desired_class","start_month",
    "guardian_name","guardian_relation",
    "phone","email","address",
    "notes","status"
]

DEFAULT_STATUS = "新送出"
STATUS_OPTIONS = ["新送出","已聯繫","已參觀","已錄取","候補","未錄取"]

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def month_str(d: date):
    return d.strftime("%Y-%m")

def normalize_phone(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\d+]", "", s)
    return s

def ensure_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=COLUMNS)
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[COLUMNS]
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    df["status"] = df["status"].fillna(DEFAULT_STATUS).astype(str)
    return df

# =========================
# Google Sheets：gspread 連線（不用 streamlit-gsheets）
# Secrets 需放：GOOGLE_SERVICE_ACCOUNT_JSON
# =========================
@st.cache_resource
def get_gspread_client():
    import gspread
    from google.oauth2.service_account import Credentials

    if "GOOGLE_SERVICE_ACCOUNT_JSON" not in st.secrets:
        raise RuntimeError("找不到 Secrets：GOOGLE_SERVICE_ACCOUNT_JSON。請到 Streamlit Secrets 貼上 service account JSON。")

    sa = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    # 允許你把 JSON 整份貼成字串或 dict
    if isinstance(sa, str):
        sa_info = json.loads(sa)
    else:
        sa_info = dict(sa)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)

def open_sheet():
    gc = get_gspread_client()
    sh = gc.open_by_url(SPREADSHEET_URL)
    ws = sh.worksheet(WORKSHEET_NAME)
    return ws

def read_sheet() -> pd.DataFrame:
    ws = open_sheet()
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=COLUMNS)
    header = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=header)
    return ensure_df(df)

def write_sheet(df: pd.DataFrame):
    ws = open_sheet()
    df = ensure_df(df)

    # 先寫 header，再寫資料
    data = [COLUMNS] + df.astype(str).values.tolist()
    ws.clear()
    ws.update("A1", data)

def append_row(row: dict):
    df = read_sheet()
    new_id = 1 if len(df) == 0 else int(df["id"].max()) + 1
    row["id"] = new_id
    df2 = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    write_sheet(df2)

# =========================
# Tabs
# =========================
tab1, tab2, tab3 = st.tabs(["📝 新生報名", "🗂️ 後台查詢", "⚙️ 系統測試"])

# =========================
# Tab 1：新生報名
# =========================
with tab1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 📝 新生報名表單")
    st.markdown('<div class="small">送出後會立刻寫入 Google 試算表的 <b>enrollments</b> 分頁。</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("enroll_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1.4, 1, 1])
        with c1:
            student_name = st.text_input("幼兒姓名 *", placeholder="例如：王小明")
        with c2:
            gender = st.selectbox("性別", ["男","女","不方便透露"], index=2)
        with c3:
            birth_date = st.date_input("出生年月日 *", value=date(2022, 1, 1))

        c4, c5 = st.columns(2)
        with c4:
            desired_class = st.selectbox("預計就讀班別 *", ["幼幼班","小班","中班","大班","不確定"])
        with c5:
            start_month = st.text_input("預計入學月份（YYYY-MM）*", value=month_str(date.today()))

        st.markdown("---")

        g1, g2, g3 = st.columns([1.2, 1, 1.2])
        with g1:
            guardian_name = st.text_input("主要聯絡人（家長）姓名 *", placeholder="例如：王爸爸")
        with g2:
            guardian_relation = st.selectbox("與幼兒關係", ["父親","母親","監護人","祖父母","其他"])
        with g3:
            phone = st.text_input("聯絡電話 *", placeholder="例如：0912-345-678")

        e1, e2 = st.columns(2)
        with e1:
            email = st.text_input("Email（選填）", placeholder="example@gmail.com")
        with e2:
            address = st.text_input("居住地址（選填）", placeholder="縣市/鄉鎮/路段...")

        notes = st.text_area("備註（選填）", placeholder="例如：過敏、想約參觀時段、是否需補助、兄姊就讀...")

        submitted = st.form_submit_button("✅ 送出報名", use_container_width=True)

    if submitted:
        errors = []
        if not student_name.strip():
            errors.append("請填寫幼兒姓名")
        if not guardian_name.strip():
            errors.append("請填寫主要聯絡人姓名")
        p = normalize_phone(phone)
        if not p or len(re.sub(r"\D", "", p)) < 9:
            errors.append("請填寫正確電話（至少 9 碼）")
        if not re.match(r"^\d{4}-\d{2}$", (start_month or "").strip()):
            errors.append("入學月份格式錯誤，請用 YYYY-MM（例如 2026-09）")

        if errors:
            st.error("⚠️ 請修正以下欄位：\n- " + "\n- ".join(errors))
        else:
            row = {
                "timestamp": now_str(),
                "student_name": student_name.strip(),
                "gender": gender,
                "birth_date": str(birth_date),
                "desired_class": desired_class,
                "start_month": (start_month or "").strip(),
                "guardian_name": guardian_name.strip(),
                "guardian_relation": guardian_relation,
                "phone": p,
                "email": (email or "").strip(),
                "address": (address or "").strip(),
                "notes": (notes or "").strip(),
                "status": DEFAULT_STATUS
            }
            try:
                append_row(row)
                st.success("✅ 已完成報名送出！我們會盡快與您聯繫。")
            except Exception as e:
                st.error("❌ 寫入失敗（通常是試算表沒分享給 service account 編輯者 / Secrets 設定錯）")
                st.code(str(e))

# =========================
# Tab 2：後台查詢
# =========================
with tab2:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 🗂️ 後台查詢與狀態管理")
    st.markdown('<div class="small">可依狀態/班別/入學月份/關鍵字篩選，並可更新狀態。</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        df = read_sheet()
    except Exception as e:
        st.error("❌ 讀取失敗（請先完成 Secrets + 分享權限）")
        st.code(str(e))
        st.stop()

    c1, c2, c3, c4 = st.columns([1, 1, 1.1, 1.6])
    with c1:
        status_filter = st.selectbox("狀態", ["全部"] + STATUS_OPTIONS)
    with c2:
        class_filter = st.selectbox("班別", ["全部","幼幼班","小班","中班","大班","不確定"])
    with c3:
        month_filter = st.text_input("入學月份（可空）", placeholder="例如 2026-09")
    with c4:
        kw = st.text_input("關鍵字（幼兒/家長/電話/備註）", placeholder="輸入關鍵字…")

    filtered = df.copy()
    if len(filtered):
        if status_filter != "全部":
            filtered = filtered[filtered["status"] == status_filter]
        if class_filter != "全部":
            filtered = filtered[filtered["desired_class"] == class_filter]
        if month_filter.strip():
            filtered = filtered[filtered["start_month"].astype(str).str.contains(month_filter.strip(), na=False)]
        if kw.strip():
            k = kw.strip()
            filtered = filtered[
                filtered["student_name"].astype(str).str.contains(k, na=False) |
                filtered["guardian_name"].astype(str).str.contains(k, na=False) |
                filtered["phone"].astype(str).str.contains(k, na=False) |
                filtered["notes"].astype(str).str.contains(k, na=False)
            ]

    k1, k2, k3 = st.columns(3)
    k1.metric("篩選後筆數", f"{len(filtered)}")
    k2.metric("不重複幼兒數", f"{filtered['student_name'].nunique() if len(filtered) else 0}")
    top_month = "-"
    if len(filtered) and filtered["start_month"].astype(str).str.len().gt(0).any():
        top_month = filtered["start_month"].value_counts().index[0]
    k3.metric("最常見入學月份", top_month)

    st.subheader("📋 名單列表")
    show_df = filtered.sort_values("id", ascending=False).copy()
    st.dataframe(show_df, use_container_width=True, hide_index=True)

    st.subheader("✏️ 更新狀態（單筆）")
    u1, u2, u3 = st.columns([1, 1.2, 1.2])
    with u1:
        target_id = st.number_input("要更新的 id", min_value=0, step=1, value=0)
    with u2:
        new_status = st.selectbox("新狀態", STATUS_OPTIONS, index=1)
    with u3:
        do_update = st.button("✅ 寫入更新", use_container_width=True)

    if do_update:
        if int(target_id) <= 0:
            st.error("請輸入正確的 id（>0）")
        else:
            try:
                base = df.copy()
                mask = base["id"] == int(target_id)
                if not mask.any():
                    st.error("找不到這個 id，請確認列表中的 id。")
                else:
                    base.loc[mask, "status"] = new_status
                    write_sheet(base)
                    st.success("✅ 已更新！")
                    st.rerun()
            except Exception as e:
                st.error("❌ 更新失敗")
                st.code(str(e))

    st.subheader("📥 匯出")
    csv_bytes = filtered.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("下載目前篩選結果 CSV", data=csv_bytes, file_name="enrollments_filtered.csv", mime="text/csv")

# =========================
# Tab 3：系統測試
# =========================
with tab3:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### ⚙️ 系統測試（讀寫確認）")
    st.markdown('<div class="small">按下按鈕會寫入一筆 TEST_時間碼，並可在 Google 表用 Ctrl+F 找到。</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("➕ 寫入 TEST 資料", use_container_width=True):
        marker = f"TEST_{datetime.now().strftime('%H%M%S')}"
        row = {
            "timestamp": now_str(),
            "student_name": marker,
            "gender": "不方便透露",
            "birth_date": "2022-01-01",
            "desired_class": "不確定",
            "start_month": "2026-09",
            "guardian_name": "TEST家長",
            "guardian_relation": "其他",
            "phone": normalize_phone("0900-000-000"),
            "email": "",
            "address": "",
            "notes": "系統測試資料，可刪",
            "status": DEFAULT_STATUS
        }
        try:
            append_row(row)
            st.success(f"✅ 已寫入：{marker}。請到 Google 試算表（enrollments）用 Ctrl+F 搜尋它。")
        except Exception as e:
            st.error("❌ 寫入失敗（通常是沒分享試算表給 service account 編輯者 / Secrets 放錯）")
            st.code(str(e))
