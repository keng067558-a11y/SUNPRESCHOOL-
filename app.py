import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import json
import time

# ==========================================
# 0. 系統介面美化 (Apple iOS 極簡風格)
# ==========================================
st.set_page_config(page_title="幼兒園招生雲端管理", page_icon="🏫", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700;900&display=swap');
    .main { background-color: #F2F2F7; }
    html, body, [class*="css"] { 
        font-family: -apple-system, "BlinkMacSystemFont", "PingFang TC", "Noto Sans TC", sans-serif !important; 
    }
    
    /* 蘋果風格統計卡片 */
    .stMetric {
        background-color: white;
        padding: 24px;
        border-radius: 24px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid rgba(0,0,0,0.05);
    }
    
    /* 按鈕樣式 */
    .stButton>button {
        border-radius: 14px;
        font-weight: 700;
        border: none;
        background-color: #007AFF;
        color: white;
        transition: all 0.2s;
        padding: 0.6rem 1.5rem;
    }
    .stButton>button:active { transform: scale(0.98); }
    
    /* 表格編輯器優化 */
    div[data-testid="stDataEditor"] {
        border-radius: 24px !important;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }

    /* 側邊欄 */
    [data-testid="stSidebar"] {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 雲端連線配置 (精準對齊您的 11 欄標題)
# ==========================================

GSHEET_ID = "1ZofZnB8Btig_6XvsHGh7bbapnfJM-vDkXTFpaU7ngmE"

# 服務帳號金鑰 (已嵌入您的專屬授權)
GOOGLE_JSON_KEY = {
  "type": "service_account",
  "project_id": "gen-lang-client-0350949155",
  "private_key_id": "0bc65fcf31f2bc625d4283024181f980b94e2d61",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQC2d0a4Jmkhn/gS\nOmYM0zbKtBMteB/pnmSqD8S0khV+9Upr1KRx2sjQ+YqYuYxa6wCX6zNCSclYTs0x\nAHg3qvEQXZ59UgUz8BWKOE59oI3o5rEDWhvBFu7KsXsugFXbgYGa4zTFGKHL7vMB\n4mtI48NwFeqZ/Jx7pJfbZ74j0hj71DWGGoKXWi8gPiC5Cj1HWDByveniWIFK5FOd\nPvcJD0e0jNPPbe/dvlyWs9vwRj6aLSyEFxoTb+uLelAQj3Mq4I6RUyzYPv+j/+5w\nvKbqbF+nox77OGvvTFdpUiY5t5PDVpObAiSSn1jGlB1dMDfJQ8G+73CK+YlKvTKf\nOjCUgZeHAgMBAAECggEAGhfciSEVD7Xsp86qIVNjFoHB7FKtXZ9FDfzLSHdLk6hI\nSDtUeOOsrBXDeCuwop/Qqej8n5IltPcv6L4EcxGC/7AjphBApjjDG80JjHWVVaUH\n007jgS1iYKIY14GKxaUzf47WUQlAugUlwzM53GaV4EWCExtI1XWoMbwYOM8mu3xT\ne8BA9cvt1a8CJjWmKgChin3qi1YEinKNudO4rJOMPCq+kVSWVEphy7XndlNWLm7E\nY5BGr+pCGGoHHlqWMotQpBuL4KzTUKom/cDj16Hk3sr8lU5wP2dXa8/ftHfSzfYp\n4THbqi9ote5CFlymVPeS6c3uEtX20ALPlg5eXA4qYQKBgQDhrGo4v7VTED01mLBk\ng2FFSigYexlHqJZRNoBuccIGgTfbKmWIDI1FQAE3klml6ZAJudejIWf902+dX7sQ\/NsnRLeNtc1Et/HnPuNVPUwMflphZ56o2BedBRZ1UXswlfKgCE0SrSjGp1cx7nsB\nS+ZoiFynEpL1PAd4tqvG+IrRewKBgQDO/HDls+Qh1i5gOLjI7pwGf3aKdVONGODa\LsNF0vPbRGeUjxgmBIZ6DdQZRUOOCw547w0IlgHBSSNLbZZOzz/9cMS0U0PXLh41\TkKaih14ZpV1kK1i/9XP1HbQlW2vLLVbD7Wzti2dOujJp1cCp9C7ZtgP7FOFlLrD\nY/fyqpc2ZQKBgQCSCIlAKcZDdwm06haTJHVIakFh/h6QwWZsLVGUpqaAoROtDlVf\YYf1XQKsnFbIx0g/EvSYiqCJn03lz7H0vzttwMjquc+X/VRbaNWhLiZNG2KPD4eb\nCSLWqBktV8nY2d+EcXq2cDknu9fv5rvQTfZOhJc4Qgu5B9xp4ANuoRzriwKBgQC7\nDDWZ3q7SRRMzsQ6LxdUJqjYdeVk/sLPBd3DPsIreIzrXbViNQpmjwstg6s7ZlfRG\nJQDKOYTsfoN+rlGednuFNFsN+hDca7iww0A9F4L6QvndfBiz1i4J2h5k8CRmoShi\nWhgBhyhBZfLoCGkA5VYjhBTMjuwLUxRTbgurJ63uYQKBgQC3NOVqMlBubI6D1/LM\nlD8HYsZxl1VsNa3wqalvqJLFgOzVSSn9UXdjNxq1Wz3VUKV5GdwVsuUWIDJ6jMyQ\nctis0id1NLpIvUNnY5VYbsX/WP/nRCUYNKfuE4LgpQoCbbmNs0bHXYUmASg4Fg/0\nUKv2TDsqoh5Yi6nl4kYEH5jSBw==\n-----END PRIVATE KEY-----\n",
  "client_email": "keng067558@gen-lang-client-0350949155.iam.gserviceaccount.com",
  "client_id": "114682091672664451195",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/keng067558%40gen-lang-client-0350949155.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# 嚴格遵循您 Excel 的 11 個標題順序
HEADERS = [
    "報名狀態", "聯繫狀態", "登記日期", "幼兒姓名", "家長稱呼", 
    "電話", "幼兒生日", "預計入學資訊", "推薦人", "備註", "重要性"
]

@st.cache_resource
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_JSON_KEY, scope)
    return gspread.authorize(creds)

def fetch_data():
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(GSHEET_ID).get_sheets()[0]
        
        # 讀取所有資料
        all_vals = sheet.get_all_values()
        
        if not all_vals or len(all_vals) == 0:
            # 初始化標題
            sheet.update(range_name='A1', values=[HEADERS])
            return pd.DataFrame(columns=HEADERS), sheet
        
        # 使用第一列作為 Header
        df = pd.DataFrame(all_vals[1:], columns=all_vals[0])
        
        # 補齊缺失欄位
        for h in HEADERS:
            if h not in df.columns:
                df[h] = ""
        
        # 確保回傳的 DataFrame 順序與 HEADERS 完全一致
        return df[HEADERS], sheet
    except Exception as e:
        st.error(f"雲端連線異常：{e}")
        return pd.DataFrame(), None

# ==========================================
# 2. 自動推算班別邏輯
# ==========================================
def calculate_grade_info(birthday_str):
    if not birthday_str or "/" not in str(birthday_str): return ""
    try:
        parts = str(birthday_str).split('/')
        roc_year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        ce_year = roc_year + 1911
        today = date.today()
        target_year = today.year if today.month < 9 else today.year + 1
        age = target_year - ce_year
        if month > 9 or (month == 9 and day >= 2): age -= 1
        
        grade_map = {2: "幼幼班", 3: "小班", 4: "中班", 5: "大班"}
        grade_name = grade_map.get(age, f"{age}歲")
        return f"{target_year - 1911} 學年 - {grade_name}"
    except: return ""

# ==========================================
# 3. 主介面 UI
# ==========================================
def main():
    # 讀取資料
    df, sheet = fetch_data()
    
    # Header
    t1, t2 = st.columns([5, 1])
    with t1:
        st.title("🏫 幼兒園雲端招生管理系統")
        st.caption("✅ 已完全對齊您的 11 欄位結構 (含推薦人、備註分開處理)")
    with t2:
        if st.button("🔄 刷新名單", use_container_width=True): 
            st.cache_resource.clear()
            st.rerun()

    if df.empty and sheet is not None:
        st.info("👋 歡迎！目前 Excel 名單是空的，請從側邊欄錄入資料。")

    # 數據統計
    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("總登記人數", len(df))
        m2.metric("待聯繫名單", len(df[df["聯繫狀態"] == '未聯繫']) if "聯繫狀態" in df.columns else 0)
        m3.metric("排隊中", len(df[df["報名狀態"] == '排隊等待']) if "報名狀態" in df.columns else 0)
        m4.metric("系統狀態", "雲端同步正常")

    st.divider()

    # 搜尋與篩選
    search = st.text_input("🔍 搜尋孩子姓名、電話、推薦人或備註", placeholder="輸入搜尋內容...")
    
    display_df = df.copy()
    if search:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        display_df = display_df[mask]

    # 名單清單與編輯區
    if not display_df.empty:
        st.subheader("📋 招生名單明細 (可直接編輯)")
        
        # 表格編輯器配置
        updated_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "報名狀態": st.column_config.SelectboxColumn("報名狀態", options=["排隊等待", "已入學", "取消報名", "候補中"]),
                "聯繫狀態": st.column_config.SelectboxColumn("聯繫進度", options=["未聯繫", "聯繫中", "已聯繫", "電話未接"]),
                "幼兒姓名": st.column_config.TextColumn("幼兒姓名", required=True),
                "推薦人": st.column_config.TextColumn("推薦人"),
                "備註": st.column_config.TextColumn("備註內容", width="large"),
                "重要性": st.column_config.SelectboxColumn("重要性", options=["高", "中", "低"]),
                "預計入學資訊": st.column_config.TextColumn("預計分班", disabled=True),
                "登記日期": st.column_config.TextColumn("登記日期", disabled=True)
            }
        )
        
        # 儲存按鈕
        if st.button("💾 儲存所有變更至雲端 Excel", type="primary"):
            try:
                with st.spinner("正在同步..."):
                    # 將資料轉為純字串列表寫回，避免格式報錯
                    final_data = updated_df.fillna("").astype(str)
                    sheet.clear()
                    # 重新寫入標題與數據
                    data_to_save = [HEADERS] + final_data.values.tolist()
                    sheet.update(range_name='A1', values=data_to_save, value_input_option='USER_ENTERED')
                    st.success("✅ 同步成功！Excel 資料已更新。")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"儲存失敗：{e}")
    else:
        st.info("目前無符合搜尋條件的數據。")

    # 側邊欄：錄入功能
    with st.sidebar:
        st.header("✨ 新增招生紀錄")
        with st.form("add_form", clear_on_submit=True):
            n_name = st.text_input("孩子姓名")
            n_parent = st.text_input("家長稱呼 (例：林媽媽)")
            n_phone = st.text_input("電話*")
            n_birth = st.text_input("生日 (例 110/05/20)")
            n_ref = st.text_input("推薦人")
            n_prio = st.selectbox("重要性", ["中", "高", "低"])
            n_note = st.text_area("詳細備註")
            
            if st.form_submit_button("立即同步寫入雲端", use_container_width=True):
                if n_phone and sheet:
                    # 自動推算入學資訊
                    entry_info = calculate_grade_info(n_birth)
                    
                    # 依照 HEADERS 11 個欄位的嚴格順序建立資料列
                    new_row = [
                        "排隊等待",           # 報名狀態
                        "未聯繫",            # 聯繫狀態
                        date.today().strftime("%Y/%m/%d"), # 登記日期
                        n_name,
                        n_parent,
                        n_phone,
                        n_birth,
                        entry_info,         # 預計入學資訊
                        n_ref,              # 推薦人
                        n_note,             # 備註
                        n_prio              # 重要性
                    ]
                    
                    try:
                        with st.spinner("正在寫入..."):
                            sheet.append_row(new_row, value_input_option='USER_ENTERED')
                            st.success(f"🎉 {n_name if n_name else '新名單'} 已錄入成功")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"寫入失敗：{e}")
                else:
                    if not sheet: st.error("雲端未連線")
                    else: st.error("電話為必填項。")

        st.divider()
        st.caption(f"📍 連動 ID：{GSHEET_ID[:10]}...")

if __name__ == "__main__":
    main()
