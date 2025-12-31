import streamlit as st
import pandas as pd
from datetime import datetime, date
from pathlib import Path
import re

# =========================
# 基本設定（Apple-ish UI）
# =========================
st.set_page_config(page_title="小太陽｜新生報名系統", page_icon="📝", layout="wide")

st.markdown("""
<style>
/* Apple-ish: 清爽留白、柔和陰影、系統字體 */
:root {
  --bg: #F5F5F7;
  --card: #FFFFFF;
  --text: #1D1D1F;
  --muted: #6E6E73;
  --line: rgba(0,0,0,0.06);
  --shadow: 0 10px 30px rgba(0,0,0,0.08);
  --radius: 18px;
}

.stApp { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display","SF Pro Text","Segoe UI","Noto Sans TC","Microsoft JhengHei", sans-serif; }

.block-container { padding-top: 1.6rem; padding-bottom: 2.2rem; }

.apple-header {
  background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(255,255,255,0.60));
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  border-radius: var(--radius);
  padding: 18px 20px;
  margin-bottom: 16px;
}

.apple-title { font-size: 1.55rem; font-weight: 800; margin: 0; letter-spacing: -0.02em; }
.apple-subtitle { color: var(--muted); margin-top: 6px; font-size: 0.95rem; }

.apple-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px 18px;
  margin-bottom: 16px;
}

.small-muted { color: var(--muted); font-size: 0.9rem; }

div[data-testid="stMetric"]{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow);
  padding: 12px 14px;
}

.stButton > button {
  border-radius: 14px;
  padding: 10px 14px;
  border: 1px solid var(--line);
  background: #111;
  color: #fff;
  font-weight: 700;
}
.stButton > button:hover { opacity: 0.92; }

div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input,
div[data-testid="stSelectbox"] > div,
div[data-testid="stNumberInput"] input {
  border-radius: 14px !important;
}

hr { border: none; border-top: 1px solid var(--line); margin: 10px 0 18px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="apple-header">
  <div class="apple-title">📝 小太陽｜新生報名系統</div>
  <div class="apple-subtitle">表單填寫 → 自動寫入 Excel → 後台可查詢、下載、替換 Excel（一步一步來）</div>
</div>
""", unsafe_allow_html=True)

# =========================
# 檔案與欄位設定（Excel 當資料庫）
# =========================
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DB_XLSX = DATA_DIR / "enrollments.xlsx"
SHEET_NAME = "enrollments"

COLUMNS = [
    "id", "timestamp",
    "student_name", "gender", "birth_date",
    "desired_class", "start_month",
    "guardian_name", "guardian_relation",
    "phone", "email",
    "address",
    "notes",
    "status"
]

DEFAULT_STATUS = "新送出"

def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def month_str(d: date) -> str:
    return d.strftime("%Y-%m")

def normalize_phone(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\d+]", "", s)
    return s

def load_db() -> pd.DataFrame:
    if not DB_XLSX.exists():
        return pd.DataFrame(columns=COLUMNS)
    try:
        df = pd.read_excel(DB_XLSX, sheet_name=SHEET_NAME, engine="openpyxl")
    except Exception:
        # 如果 Excel 沒有 sheet 或格式怪，回空表避免整個 app 壞掉
        return pd.DataFrame(columns=COLUMNS)

    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""

    # 基本型別整理
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
    df["timestamp"] = df["timestamp"].astype(str)
    df["student_name"] = df["student_name"].astype(str)
    df["phone"] = df["phone"].astype(str)
    df["status"] = df["status"].fillna(DEFAULT_STATUS).astype(str)

    return df[COLUMNS]

def save_db(df: pd.DataFrame):
    df = df.copy()
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[COLUMNS]
    with pd.ExcelWriter(DB_XLSX, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=SHEET_NAME, index=False)

def next_id(df: pd.DataFrame) -> int:
    if len(df) == 0:
        return 1
    return int(df["id"].max()) + 1

def add_enrollment(row: dict):
    df = load_db()
    row["id"] = next_id(df)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_db(df)

# =========================
# 介面：Tabs
# =========================
tab1, tab2, tab3 = st.tabs(["📝 新生報名", "🗂️ 後台查詢", "⚙️ 連結/替換 Excel"])

# =========================
# Tab 1：新生報名表單
# =========================
with tab1:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 📝 新生報名資料（家長填寫）")
    st.markdown('<div class="small-muted">送出後會寫入系統 Excel（enrollments.xlsx）。</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.form("enroll_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1.2, 1, 1])

        with c1:
            student_name = st.text_input("幼兒姓名 *", placeholder="例如：王小明")
        with c2:
            gender = st.selectbox("性別", ["男", "女", "不方便透露"], index=2)
        with c3:
            birth_date = st.date_input("出生年月日 *", value=date(2022, 1, 1))

        c4, c5 = st.columns(2)
        with c4:
            desired_class = st.selectbox("預計就讀班別 *", ["幼幼班", "小班", "中班", "大班", "不確定"])
        with c5:
            start_month = st.text_input("預計入學月份（YYYY-MM）*", value=month_str(date.today()))

        st.markdown("---")

        g1, g2, g3 = st.columns([1, 1, 1])
        with g1:
            guardian_name = st.text_input("主要聯絡人（家長）姓名 *", placeholder="例如：王爸爸")
        with g2:
            guardian_relation = st.selectbox("與幼兒關係", ["父親", "母親", "監護人", "祖父母", "其他"])
        with g3:
            phone = st.text_input("聯絡電話 *", placeholder="例如：0912-345-678")

        e1, e2 = st.columns(2)
        with e1:
            email = st.text_input("Email（選填）", placeholder="example@gmail.com")
        with e2:
            address = st.text_input("居住地址（選填）", placeholder="縣市/鄉鎮/路段...")

        notes = st.text_area("備註（選填）", placeholder="例如：過敏、想了解參觀時間、需要補助資訊...")

        submitted = st.form_submit_button("✅ 送出報名", use_container_width=True)

    if submitted:
        # 基本檢核
        errors = []
        if not student_name.strip():
            errors.append("請填寫幼兒姓名")
        if not guardian_name.strip():
            errors.append("請填寫主要聯絡人姓名")
        phone_n = normalize_phone(phone)
        if not phone_n or len(re.sub(r"\D", "", phone_n)) < 9:
            errors.append("請填寫正確的聯絡電話（至少 9 碼）")
        if not re.match(r"^\d{4}-\d{2}$", (start_month or "").strip()):
            errors.append("入學月份格式錯誤，請用 YYYY-MM（例如 2026-09）")

        if errors:
            st.error("⚠️ 請修正以下欄位：\n- " + "\n- ".join(errors))
        else:
            row = {
                "id": 0,  # 會自動補
                "timestamp": now_str(),
                "student_name": student_name.strip(),
                "gender": gender,
                "birth_date": str(birth_date),
                "desired_class": desired_class,
                "start_month": (start_month or "").strip(),
                "guardian_name": guardian_name.strip(),
                "guardian_relation": guardian_relation,
                "phone": phone_n,
                "email": (email or "").strip(),
                "address": (address or "").strip(),
                "notes": (notes or "").strip(),
                "status": DEFAULT_STATUS
            }
            add_enrollment(row)
            st.success("✅ 已完成報名送出！我們會盡快與您聯繫。")

# =========================
# Tab 2：後台查詢
# =========================
with tab2:
    df = load_db()

    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### 🗂️ 後台查詢（管理者）")
    st.markdown(f'<div class="small-muted">目前總筆數：{len(df)}　｜　資料檔：<code>{DB_XLSX.as_posix()}</code></div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([1, 1, 1.2, 1.2])
    with c1:
        status_filter = st.selectbox("狀態", ["全部", "新送出", "已聯繫", "已參觀", "已錄取", "候補", "未錄取"])
    with c2:
        class_filter = st.selectbox("班別", ["全部", "幼幼班", "小班", "中班", "大班", "不確定"])
    with c3:
        month_filter = st.text_input("入學月份（YYYY-MM，可空）", placeholder="例如 2026-09")
    with c4:
        kw = st.text_input("關鍵字（姓名/電話/備註）", placeholder="輸入關鍵字...")

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
    k3.metric("本週新增（概估）", f"{(filtered['timestamp'].astype(str).str.contains(datetime.now().strftime('%Y-%m-%d')).sum() if len(filtered) else 0)}")

    st.subheader("📋 報名名單")
    st.dataframe(
        filtered.sort_values("id", ascending=False),
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📥 匯出")
    # 下載 Excel（整庫）
    if DB_XLSX.exists():
        st.download_button(
            "下載目前系統 Excel（整庫）",
            data=DB_XLSX.read_bytes(),
            file_name="enrollments.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    # 下載篩選結果 CSV
    csv_bytes = filtered.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "下載目前篩選結果 CSV",
        data=csv_bytes,
        file_name="enrollments_filtered.csv",
        mime="text/csv"
    )

# =========================
# Tab 3：連結/替換 Excel（教你換新的資料庫）
# =========================
with tab3:
    st.markdown('<div class="apple-card">', unsafe_allow_html=True)
    st.markdown("### ⚙️ 連結 / 替換 Excel（把你的新 Excel 變成系統資料庫）")
    st.markdown("""
<div class="small-muted">
你可以：
<br>1) 下載「空白範本 Excel」，照欄位填資料再上傳
<br>2) 直接上傳你自己的 Excel（只要欄位名稱對得上）
</div>
""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # 下載範本
    template_df = pd.DataFrame(columns=COLUMNS)
    tmp_path = DATA_DIR / "template_enrollments.xlsx"
    with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
        template_df.to_excel(writer, sheet_name=SHEET_NAME, index=False)

    st.download_button(
        "📄 下載空白範本 Excel（template）",
        data=tmp_path.read_bytes(),
        file_name="template_enrollments.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")

    uploaded = st.file_uploader("⬆️ 上傳你的 Excel（會直接取代系統 enrollments.xlsx）", type=["xlsx"])

    if uploaded is not None:
        try:
            up_bytes = uploaded.getvalue()
            # 先讀進來檢查欄位
            test_df = pd.read_excel(up_bytes, sheet_name=SHEET_NAME, engine="openpyxl")
            missing = [c for c in COLUMNS if c not in test_df.columns]
            if missing:
                st.error("❌ 你的 Excel 欄位不完整，缺少：\n- " + "\n- ".join(missing))
                st.info("建議：先下載『空白範本 Excel』，把你的資料貼到範本欄位中再上傳。")
            else:
                # 存成系統資料庫
                DB_XLSX.write_bytes(up_bytes)
                st.success("✅ 已成功替換系統 Excel！回到『後台查詢』就會看到新資料。")
                st.rerun()
        except Exception as e:
            st.error(f"❌ 讀取/替換失敗：{e}")

    st.markdown("---")
    st.markdown("#### 🧹 清空系統資料（慎用）")
    if st.button("清空（重建空白 enrollments.xlsx）", use_container_width=True):
        save_db(pd.DataFrame(columns=COLUMNS))
        st.success("✅ 已清空並重建空白資料庫。")
        st.rerun()
