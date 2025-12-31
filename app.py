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
# 1) Apple 風格 UI
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
.block-container{ max-width:1180px; padding-top:1.1rem; padding-bottom:2rem; }
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

.k-card{
  background:#fff;
  border:1px solid rgba(0,0,0,0.06);
  border-radius:18px;
  box-shadow:0 10px 26px rgba(0,0,0,0.06);
  padding:14px 14px 12px 14px;
  margin-bottom:12px;
}
.k-title{
  font-size:1.05rem; font-weight:900; letter-spacing:-0.01em; margin:0; color:#1D1D1F;
}
.k-sub{ margin-top:4px; color:#6E6E73; font-size:.9rem; }
.k-row{ margin-top:10px; display:flex; flex-wrap:wrap; gap:6px; }

.badge{
  display:inline-block;
  padding:4px 10px;
  border-radius:999px;
  font-size:.82rem;
  border:1px solid rgba(0,0,0,.08);
  background:rgba(0,0,0,.03);
  color:#1D1D1F;
}
.badge-ok{ background:rgba(52,199,89,.12); border-color:rgba(52,199,89,.22); }
.badge-warn{ background:rgba(255,149,0,.12); border-color:rgba(255,149,0,.22); }
.badge-danger{ background:rgba(255,59,48,.12); border-color:rgba(255,59,48,.22); }

.k-meta{ margin-top:10px; color:#1D1D1F; font-size:.9rem; line-height:1.35; }
.k-meta span{ color:#6E6E73; }

.idpill{
  display:inline-block; margin-left:8px;
  padding:3px 10px; border-radius:999px;
  font-size:.78rem; border:1px solid rgba(0,0,0,.08);
  background:rgba(0,0,0,.03); color:#1D1D1F;
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
# 2) Google Sheet 欄位（加上：學年度 / 預計班別 / 確認就讀）
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
    "學年度",      # ✅ 新增
    "預計班別",    # ✅ 新增（幼幼/小班/中班/大班）
    "確認就讀",    # ✅ 新增（是/否）
]

REPORT_STATUS = ["新登記", "已入學", "候補", "不錄取"]
CONTACT_STATUS = ["未聯繫", "已聯繫", "已參觀", "無回應"]
IMPORTANCE = ["高", "中", "低"]
SCHOOL_YEAR = ["114", "115", "116"]
CLASS_LEVEL = ["幼幼", "小班", "中班", "大班"]
CONFIRM = ["否", "是"]

DEFAULT_ROW = {
    "報名狀態": "新登記",
    "聯繫狀態": "未聯繫",
    "重要性": "中",
    "學年度": "115",
    "預計班別": "幼幼",
    "確認就讀": "否",
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
    df = df[COLUMNS].copy()

    # 去掉空列
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

def safe(v):
    return "" if v is None else str(v).strip()

def badge_for_importance(v: str) -> str:
    v = (v or "").strip()
    if v == "高":
        return "badge badge-danger"
    if v == "中":
        return "badge badge-warn"
    if v == "低":
        return "badge badge-ok"
    return "badge"

def badge_for_confirm(v: str) -> str:
    return "badge badge-ok" if (v or "").strip() == "是" else "badge"

# =========================
# 5) 主分頁
# =========================
tab_enroll, tab_placeholder = st.tabs(["新生登記", "（其他模組）"])

with tab_enroll:
    t_form, t_list = st.tabs(["表單", "名單"])

    # ---------- 表單 ----------
    with t_form:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 新生登記")
        st.markdown("</div>", unsafe_allow_html=True)

        with st.form("enroll_form", clear_on_submit=True):
            a, b, c = st.columns([1, 1, 1])
            with a:
                report_status = st.selectbox("報名狀態", REPORT_STATUS, index=0)
            with b:
                contact_status = st.selectbox("聯繫狀態", CONTACT_STATUS, index=0)
            with c:
                importance = st.selectbox("重要性", IMPORTANCE, index=1)

            d, e, f = st.columns([1, 1, 1])
            with d:
                school_year = st.selectbox("學年度", SCHOOL_YEAR, index=SCHOOL_YEAR.index("115"))
            with e:
                class_level = st.selectbox("預計班別", CLASS_LEVEL, index=0)
            with f:
                confirm = st.selectbox("確認就讀", CONFIRM, index=0)

            g, h = st.columns(2)
            with g:
                child_name = st.text_input("幼兒姓名 *", placeholder="例如：王小明")
            with h:
                parent_title = st.text_input("家長稱呼 *", placeholder="例如：王爸爸／王媽媽")

            i, j = st.columns(2)
            with i:
                phone = st.text_input("電話 *", placeholder="例如：0912345678")
            with j:
                child_bday = st.date_input("幼兒生日 *", value=date(2022, 1, 1))

            enroll_info = st.text_input("預計入學資訊", placeholder="例如：115學年度小班／2026-09")
            referrer = st.text_input("推薦人", placeholder="選填")
            notes = st.text_area("備註", placeholder="選填")

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
                row["學年度"] = school_year
                row["預計班別"] = class_level
                row["確認就讀"] = confirm

                try:
                    append_row(row)
                    st.success("已送出")
                except Exception as e:
                    st.error("寫入失敗")
                    st.code(str(e))

    # ---------- 名單 ----------
    with t_list:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 名單")
        st.markdown('<div class="small">未聯繫 / 已聯繫 / 115確認就讀</div>', unsafe_allow_html=True)
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
            # 加上年齡段排序用
            tmp = df.copy()
            tmp["月齡"] = tmp["幼兒生日"].apply(calc_age_months)
            tmp["年齡段"] = tmp["月齡"].apply(age_band_from_months)

            # 三個視角
            v1, v2, v3 = st.tabs(["未聯繫", "已聯繫", "115 確認就讀名單"])

            def render_cards(data: pd.DataFrame, title_hint: str = ""):
                band_order = ["0–1歲","1–2歲","2–3歲","3–4歲","4–5歲","5–6歲","6歲以上","未知"]
                data["年齡段"] = pd.Categorical(data["年齡段"], categories=band_order, ordered=True)
                data = data.sort_values(["年齡段", "月齡"], ascending=[True, True]).reset_index(drop=True)

                if title_hint:
                    st.caption(title_hint)

                for band in band_order:
                    group = data[data["年齡段"] == band]
                    if len(group) == 0:
                        continue

                    with st.expander(f"{band}（{len(group)}）", expanded=True):
                        cols = st.columns(3)
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
                            imp_badge = badge_for_importance(imp)
                            conf = safe(r.get("確認就讀"))
                            conf_badge = badge_for_confirm(conf)

                            html = f"""
                            <div class="k-card">
                              <div class="k-title">{safe(r.get("幼兒姓名"))}<span class="idpill">{safe(r.get("編號"))}</span></div>
                              <div class="k-sub">{age_text}</div>

                              <div class="k-row">
                                <span class="badge">報名：{safe(r.get("報名狀態")) or "—"}</span>
                                <span class="badge">聯繫：{safe(r.get("聯繫狀態")) or "—"}</span>
                                <span class="{imp_badge}">重要性：{imp or "—"}</span>
                                <span class="badge">學年度：{safe(r.get("學年度")) or "—"}</span>
                                <span class="badge">班別：{safe(r.get("預計班別")) or "—"}</span>
                                <span class="{conf_badge}">確認就讀：{conf or "—"}</span>
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
                            cols[i % 3].markdown(html, unsafe_allow_html=True)
                            i += 1

            # --- 未聯繫 ---
            with v1:
                data = tmp[tmp["聯繫狀態"].astype(str).fillna("") == "未聯繫"].copy()
                if len(data) == 0:
                    st.info("目前沒有未聯繫資料")
                else:
                    render_cards(data, "只顯示：聯繫狀態＝未聯繫")

            # --- 已聯繫 ---
            with v2:
                data = tmp[tmp["聯繫狀態"].astype(str).fillna("") != "未聯繫"].copy()
                if len(data) == 0:
                    st.info("目前沒有已聯繫資料")
                else:
                    render_cards(data, "只顯示：聯繫狀態≠未聯繫")

            # --- 115 確認就讀名單（依班別分組）---
            with v3:
                data = tmp[
                    (tmp["學年度"].astype(str).fillna("") == "115") &
                    (tmp["確認就讀"].astype(str).fillna("") == "是")
                ].copy()

                if len(data) == 0:
                    st.info("目前 115 學年度尚無『確認就讀』名單")
                else:
                    st.markdown("#### 115 確認就讀名單（依班別）")
                    for lv in CLASS_LEVEL:
                        g = data[data["預計班別"].astype(str).fillna("") == lv].copy()
                        with st.expander(f"{lv}（{len(g)}）", expanded=True):
                            if len(g) == 0:
                                st.caption("目前沒有")
                            else:
                                # 這裡就不用再分年齡段了，直接卡片排
                                cols = st.columns(3)
                                i = 0
                                for _, r in g.iterrows():
                                    imp = safe(r.get("重要性"))
                                    html = f"""
                                    <div class="k-card">
                                      <div class="k-title">{safe(r.get("幼兒姓名"))}<span class="idpill">{safe(r.get("編號"))}</span></div>
                                      <div class="k-sub">家長：{safe(r.get("家長稱呼")) or "—"}　電話：{safe(r.get("電話")) or "—"}</div>
                                      <div class="k-row">
                                        <span class="badge">報名：{safe(r.get("報名狀態")) or "—"}</span>
                                        <span class="badge">聯繫：{safe(r.get("聯繫狀態")) or "—"}</span>
                                        <span class="{badge_for_importance(imp)}">重要性：{imp or "—"}</span>
                                        <span class="badge badge-ok">確認就讀：是</span>
                                      </div>
                                      <div class="k-meta">
                                        <div><span>登記：</span>{safe(r.get("登記日期")) or "—"}</div>
                                        <div><span>預計入學：</span>{safe(r.get("預計入學資訊")) or "—"}</div>
                                        <div><span>推薦人：</span>{safe(r.get("推薦人")) or "—"}</div>
                                        <div><span>備註：</span>{safe(r.get("備註")) or "—"}</div>
                                      </div>
                                    </div>
                                    """
                                    cols[i % 3].markdown(html, unsafe_allow_html=True)
                                    i += 1

            # ---------- 更新（用編號定位） ----------
            st.markdown("---")
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 更新")
            st.markdown("</div>", unsafe_allow_html=True)

            id_list = df["編號"].astype(str).tolist()
            target_id = st.selectbox("選擇編號", id_list)

            row_idx = df.index[df["編號"].astype(str) == str(target_id)].tolist()[0]

            cur_report = df.loc[row_idx, "報名狀態"] or "新登記"
            cur_contact = df.loc[row_idx, "聯繫狀態"] or "未聯繫"
            cur_imp = df.loc[row_idx, "重要性"] or "中"
            cur_year = df.loc[row_idx, "學年度"] or "115"
            cur_class = df.loc[row_idx, "預計班別"] or "幼幼"
            cur_confirm = df.loc[row_idx, "確認就讀"] or "否"

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

            d, e, f = st.columns(3)
            with d:
                new_year = st.selectbox("學年度", SCHOOL_YEAR,
                                        index=SCHOOL_YEAR.index(cur_year) if cur_year in SCHOOL_YEAR else 1)
            with e:
                new_class = st.selectbox("預計班別", CLASS_LEVEL,
                                         index=CLASS_LEVEL.index(cur_class) if cur_class in CLASS_LEVEL else 0)
            with f:
                new_confirm = st.selectbox("確認就讀", CONFIRM,
                                           index=CONFIRM.index(cur_confirm) if cur_confirm in CONFIRM else 0)

            if st.button("儲存", use_container_width=True):
                try:
                    update_cell_by_row_index(row_idx, "報名狀態", new_report)
                    update_cell_by_row_index(row_idx, "聯繫狀態", new_contact)
                    update_cell_by_row_index(row_idx, "重要性", new_imp)
                    update_cell_by_row_index(row_idx, "學年度", new_year)
                    update_cell_by_row_index(row_idx, "預計班別", new_class)
                    update_cell_by_row_index(row_idx, "確認就讀", new_confirm)
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
