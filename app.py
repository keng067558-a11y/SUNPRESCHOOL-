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

/* 卡片 */
.k-card{
  background:#fff;
  border:1px solid rgba(0,0,0,0.06);
  border-radius:18px;
  box-shadow:0 10px 26px rgba(0,0,0,0.06);
  padding:14px 14px 12px 14px;
  margin-bottom:12px;
}
.k-title{
  font-size:1.05rem;
  font-weight:900;
  letter-spacing:-0.01em;
  margin:0;
  color:#1D1D1F;
}
.k-sub{
  margin-top:4px;
  color:#6E6E73;
  font-size:.9rem;
}
.k-row{
  margin-top:10px;
  display:flex;
  flex-wrap:wrap;
  gap:6px;
}
.badge{
  display:inline-block;
  padding:4px 10px;
  border-radius:999px;
  font-size:.82rem;
  border:1px solid rgba(0,0,0,.08);
  background:rgba(0,0,0,.03);
  color:#1D1D1F;
}
.badge-hi{ background:rgba(255,59,48,.10); border-color:rgba(255,59,48,.18); }
.badge-mid{ background:rgba(255,149,0,.10); border-color:rgba(255,149,0,.18); }
.badge-low{ background:rgba(52,199,89,.10); border-color:rgba(52,199,89,.18); }

.k-meta{
  margin-top:10px;
  color:#1D1D1F;
  font-size:.9rem;
  line-height:1.35;
}
.k-meta span{ color:#6E6E73; }

.idpill{
  display:inline-block;
  margin-left:8px;
  padding:3px 10px;
  border-radius:999px;
  font-size:.78rem;
  border:1px solid rgba(0,0,0,.08);
  background:rgba(0,0,0,.03);
  color:#1D1D1F;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="topbar">
  <div class="brand">
    <div class="logo">🏫</div>
    <div>
      <div class="title">小太陽｜幼兒園管理系統</div>
      <div class="small">新生登記</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================
# 2) Google Sheet 設定（依你最新欄位順序）
# =========================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Pz7z9CdU8MODTdXbckXCnI0NpjXquZDcZCC-DTOen3o/edit?usp=sharing"
WORKSHEET_NAME = "enrollments"

COLUMNS = [
    "編號",
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
    # 直接覆蓋第一列，確保欄位順序正確
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
    df = df[COLUMNS].copy()

    # 去掉整列空白
    df = df[~(df.fillna("").astype(str).apply(lambda r: "".join(r.values).strip() == "", axis=1))].copy()
    df.reset_index(drop=True, inplace=True)
    return df

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

def gen_id(phone_clean: str) -> str:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    last4 = (phone_clean[-4:] if phone_clean else "0000")
    return f"EN{ts}{last4}"

def parse_date_any(x: str):
    try:
        d = pd.to_datetime(str(x), errors="coerce")
        if pd.isna(d):
            return None
        return d.date()
    except Exception:
        return None

def calc_age_months(birthday_str: str):
    b = parse_date_any(birthday_str)
    if not b:
        return None
    today = date.today()
    days = (today - b).days
    if days < 0:
        return None
    return int(days / 30.44)

def age_band_from_months(m):
    if m is None:
        return "未知"
    years = m // 12
    if years >= 6:
        return "6歲以上"
    return f"{years}–{years+1}歲"

def importance_badge_class(v: str) -> str:
    v = (v or "").strip()
    if v == "高":
        return "badge badge-hi"
    if v == "中":
        return "badge badge-mid"
    if v == "低":
        return "badge badge-low"
    return "badge"

def safe(v):
    return "" if v is None else str(v).strip()

# =========================
# 5) 管理系統分頁：新生登記
# =========================
tab_enroll, tab_placeholder = st.tabs(["新生登記", "（其他模組）"])

with tab_enroll:
    t1, t2 = st.tabs(["表單", "名單"])

    # ---------- 表單 ----------
    with t1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 新生登記")
        st.markdown("</div>", unsafe_allow_html=True)

        with st.form("enroll_form", clear_on_submit=True):
            c0, c1 = st.columns([1, 2])
            with c0:
                report_status = st.selectbox("報名狀態", REPORT_STATUS, index=0)
            with c1:
                contact_status = st.selectbox("聯繫狀態", CONTACT_STATUS, index=0)

            c2, c3 = st.columns(2)
            with c2:
                child_name = st.text_input("幼兒姓名 *", placeholder="例如：王小明")
            with c3:
                parent_title = st.text_input("家長稱呼 *", placeholder="例如：王爸爸／王媽媽")

            c4, c5 = st.columns(2)
            with c4:
                phone = st.text_input("電話 *", placeholder="例如：0912345678")
            with c5:
                child_bday = st.date_input("幼兒生日 *", value=date(2022, 1, 1))

            enroll_info = st.text_input("預計入學資訊", placeholder="例如：114學年度小班／2026-09")
            referrer = st.text_input("推薦人", placeholder="選填")
            notes = st.text_area("備註", placeholder="選填")

            c6, c7 = st.columns([1, 1])
            with c6:
                importance = st.selectbox("重要性", IMPORTANCE, index=1)
            with c7:
                st.caption("※ 編號會自動產生")

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

                row["編號"] = gen_id(phone_clean)
                row["報名狀態"] = report_status
                row["聯繫狀態"] = contact_status
                row["登記日期"] = now_str()
                row["幼兒姓名"] = child_name.strip()
                row["家長稱呼"] = parent_title.strip()
                row["電話"] = phone_clean
                row["幼兒生日"] = str(child_bday)
                row["預計入學資訊"] = (enroll_info or "").strip()
                row["推薦人"] = (referrer or "").strip()
                row["備註"] = (notes or "").strip()
                row["重要性"] = importance

                try:
                    append_row(row)
                    st.success("已送出")
                except Exception as e:
                    st.error("寫入失敗")
                    st.code(str(e))

    # ---------- 名單（卡片 + 分年齡段） ----------
    with t2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 名單")
        st.markdown('<div class="small">依年齡段分區顯示</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        try:
            df = read_df()
        except Exception as e:
            st.error("讀取失敗")
            st.code(str(e))
            st.stop()

        if len(df) == 0:
            st.info("目前沒有資料")
        else:
            tmp = df.copy()
            tmp["月齡"] = tmp["幼兒生日"].apply(calc_age_months)
            tmp["年齡段"] = tmp["月齡"].apply(age_band_from_months)

            band_order = ["0–1歲","1–2歲","2–3歲","3–4歲","4–5歲","5–6歲","6歲以上","未知"]
            tmp["年齡段"] = pd.Categorical(tmp["年齡段"], categories=band_order, ordered=True)
            tmp = tmp.sort_values(["年齡段", "月齡"], ascending=[True, True]).reset_index(drop=True)

            # 篩選
            top = st.columns([1.3, 1.2, 1.2, 1.2, 1.3])
            with top[0]:
                pick_band = st.selectbox("年齡段", ["全部"] + band_order, index=0)
            with top[1]:
                pick_report = st.selectbox("報名狀態", ["全部"] + REPORT_STATUS, index=0)
            with top[2]:
                pick_contact = st.selectbox("聯繫狀態", ["全部"] + CONTACT_STATUS, index=0)
            with top[3]:
                pick_imp = st.selectbox("重要性", ["全部"] + IMPORTANCE, index=0)
            with top[4]:
                kw = st.text_input("關鍵字", placeholder="幼兒/家長/電話/備註/推薦人/編號")

            view = tmp.copy()
            if pick_band != "全部":
                view = view[view["年齡段"] == pick_band]
            if pick_report != "全部":
                view = view[view["報名狀態"] == pick_report]
            if pick_contact != "全部":
                view = view[view["聯繫狀態"] == pick_contact]
            if pick_imp != "全部":
                view = view[view["重要性"] == pick_imp]
            if kw.strip():
                k = kw.strip()
                view = view[
                    view["幼兒姓名"].astype(str).str.contains(k, na=False) |
                    view["家長稱呼"].astype(str).str.contains(k, na=False) |
                    view["電話"].astype(str).str.contains(k, na=False) |
                    view["備註"].astype(str).str.contains(k, na=False) |
                    view["推薦人"].astype(str).str.contains(k, na=False) |
                    view["預計入學資訊"].astype(str).str.contains(k, na=False) |
                    view["編號"].astype(str).str.contains(k, na=False)
                ]

            for band in band_order:
                group = view[view["年齡段"] == band]
                if len(group) == 0:
                    continue

                with st.expander(f"{band}（{len(group)}）", expanded=True):
                    cols_per_row = 3
                    cols = st.columns(cols_per_row)
                    i = 0

                    for _, r in group.iterrows():
                        m = r.get("月齡")
                        if pd.isna(m) or m is None:
                            age_text = "年齡：—"
                        else:
                            y = int(m) // 12
                            mm = int(m) % 12
                            age_text = f"年齡：{y}歲{mm}月"

                        imp = safe(r.get("重要性"))
                        imp_cls = importance_badge_class(imp)

                        html = f"""
                        <div class="k-card">
                          <div class="k-title">{safe(r.get("幼兒姓名"))}<span class="idpill">{safe(r.get("編號"))}</span></div>
                          <div class="k-sub">{age_text}</div>

                          <div class="k-row">
                            <span class="badge">報名：{safe(r.get("報名狀態")) or "—"}</span>
                            <span class="badge">聯繫：{safe(r.get("聯繫狀態")) or "—"}</span>
                            <span class="{imp_cls}">重要性：{imp or "—"}</span>
                          </div>

                          <div class="k-meta">
                            <div><span>家長：</span>{safe(r.get("家長稱呼")) or "—"}　<span>電話：</span>{safe(r.get("電話")) or "—"}</div>
                            <div><span>登記：</span>{safe(r.get("登記日期")) or "—"}</div>
                            <div><span>預計入學：</span>{safe(r.get("預計入學資訊")) or "—"}</div>
                            <div><span>推薦人：</span>{safe(r.get("推薦人")) or "—"}</div>
                            <div><span>備註：</span>{safe(r.get("備註")) or "—"}</div>
                          </div>
                        </div>
                        """
                        cols[i % cols_per_row].markdown(html, unsafe_allow_html=True)
                        i += 1

            st.markdown("---")

            # 更新：用「編號」定位
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 更新")
            st.markdown("</div>", unsafe_allow_html=True)

            id_list = df["編號"].astype(str).tolist()
            target_id = st.selectbox("選擇編號", id_list)

            row_idx = df.index[df["編號"].astype(str) == str(target_id)].tolist()[0]
            cur_report = df.loc[row_idx, "報名狀態"] or "新登記"
            cur_contact = df.loc[row_idx, "聯繫狀態"] or "未聯繫"
            cur_imp = df.loc[row_idx, "重要性"] or "中"

            a, b, c = st.columns(3)
            with a:
                new_report = st.selectbox("報名狀態", REPORT_STATUS,
                                          index=REPORT_STATUS.index(cur_report) if cur_report in REPORT_STATUS else 0)
            with b:
                new_contact = st.selectbox("聯繫狀態", CONTACT_STATUS,
                                           index=CONTACT_STATUS.index(cur_contact) if cur_contact in CONTACT_STATUS else 0)
            with c:
                new_imp = st.selectbox("重要性", IMPORTANCE,
                                       index=IMPORTANCE.index(cur_imp) if cur_imp in IMPORTANCE else 1)

            if st.button("儲存", use_container_width=True):
                try:
                    update_cell_by_row_index(row_idx, "報名狀態", new_report)
                    update_cell_by_row_index(row_idx, "聯繫狀態", new_contact)
                    update_cell_by_row_index(row_idx, "重要性", new_imp)
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
