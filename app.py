import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import json
import time

# ==========================================
# 0. 系統介面美化 (Apple 極簡美學)
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
    
    /* 表格編輯器優化 */
    div[data-testid="stDataEditor"] {
        border-radius: 24px !important;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }

    /* 側邊欄背景 */
    [data-testid="stSidebar"] {
        background-color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 雲端連線配置 (精準對齊 10 欄結構)
# ==========================================

GSHEET_ID = "1ZofZnB8Btig_6XvsHGh7bbapnfJM-vDkXTFpaU7ngmE"

# 服務帳號金鑰
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

# 嚴格對齊 10 欄標題 (已移除推薦人)
HEADERS = [
    "報名狀態", "聯繫狀態", "登記日期", "幼兒姓名", "家長稱呼", 
    "電話", "幼兒生日", "預計入學資訊", "備註", "重要性"
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
        data = sheet.get_all_records()
        
        # 若 Excel 是空的，初始化標題
        if not data and not sheet.get_all_values():
            sheet.update(range_name='A1', values=[HEADERS])
            return pd.DataFrame(columns=HEADERS), sheet
            
        return pd.DataFrame(data), sheet
    except Exception as e:
        st.error(f"雲端連線失敗，請確認已共用給金鑰 Email：{e}")
        return pd.DataFrame(), None

# ==========================================
# 2. 班別計算邏輯 (台灣 9/1 學制)
# ==========================================
def calculate_grade_info(birthday_str):
    if not birthday_str or "/" not in str(birthday_str): return ""
    try:
        parts = str(birthday_str).split('/')
        roc_year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        ce_year = roc_year + 1911
        today = date.today()
        # 決定目標基準年 (以此學年度 9/1 為準)
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
    df, sheet = fetch_data()
    
    # 頂部導覽列
    t1, t2 = st.columns([5, 1])
    with t1:
        st.title("🏫 幼兒園招生雲端管理系統")
        st.caption("✅ 已對齊 10 欄位結構 (推薦資訊已併入備註)")
    with t2:
        if st.button("🔄 刷新名單", use_container_width=True): 
            st.cache_resource.clear()
            st.rerun()

    if df.empty and sheet is not None:
        st.info("👋 歡迎！目前雲端名單是空的，請從左側邊欄錄入第一筆新生資料。")

    # A. 數據統計看板
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("總登記人數", len(df))
    m2.metric("待聯繫名單", len(df[df["聯繫狀態"] == '未聯繫']) if not df.empty and "聯繫狀態" in df.columns else 0)
    m3.metric("排隊等待中", len(df[df["報名狀態"] == '排隊等待']) if not df.empty and "報名狀態" in df.columns else 0)
    m4.metric("系統狀態", "雲端同步中")

    st.divider()

    # B. 搜尋篩選區
    search = st.text_input("🔍 搜尋 (姓名、電話、家長稱呼或備註內容)", placeholder="輸入關鍵字...")
    
    display_df = df.copy()
    if search:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        display_df = display_df[mask]

    # C. 名單清單與編輯
    if not display_df.empty:
        st.subheader("📋 招生名單明細 (可直接編輯內容)")
        
        # 確保顯示順序符合 HEADERS
        available_cols = [c for c in HEADERS if c in display_df.columns]
        display_df = display_df[available_cols]
        
        # 表格編輯器
        updated_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "報名狀態": st.column_config.SelectboxColumn("報名狀態", options=["排隊等待", "已入學", "取消報名", "候補中"]),
                "聯繫狀態": st.column_config.SelectboxColumn("聯繫狀態", options=["未聯繫", "聯繫中", "已聯繫", "電話未接"]),
                "幼兒姓名": st.column_config.TextColumn("幼兒姓名", required=True),
                "重要性": st.column_config.SelectboxColumn("重要性", options=["高", "中", "低"]),
                "備註": st.column_config.TextColumn("備註內容 (含推薦資訊)", width="large"),
                "預計入學資訊": st.column_config.TextColumn("系統推算班別"),
                "登記日期": st.column_config.TextColumn("登記日期", disabled=True)
            }
        )
        
        # 儲存同步按鈕
        if st.button("💾 儲存所有變更並同步至 Excel", type="primary"):
            try:
                with st.spinner("同步至雲端 Excel 中..."):
                    sheet.clear()
                    # 重新寫入完整的標題與數據
                    data_to_save = [updated_df.columns.values.tolist()] + updated_df.values.tolist()
                    sheet.update(range_name='A1', values=data_to_save, value_input_option='USER_ENTERED')
                    st.success("✅ 同步成功！雲端資料已即時更新。")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"儲存失敗：{e}")
    else:
        st.info("目前尚無符合搜尋條件的資料數據。")

    # D. 側邊欄：新增登記功能
    with st.sidebar:
        st.header("✨ 錄入新生登記")
        with st.form("add_form", clear_on_submit=True):
            n_name = st.text_input("幼兒姓名")
            n_parent = st.text_input("家長稱呼 (例：林媽媽)")
            n_phone = st.text_input("聯絡電話*")
            n_birth = st.text_input("幼兒生日 (例 110/01/01)")
            n_prio = st.selectbox("重要性", ["中", "高", "低"])
            n_note = st.text_area("詳細備註 (建議包含推薦人資訊)")
            
            if st.form_submit_button("立即同步寫入雲端", use_container_width=True):
                if n_phone:
                    # 自動推算入學資訊
                    entry_info = calculate_grade_info(n_birth)
                    
                    # 按照 10 個欄位的嚴格順序建立新資料列
                    new_row = [
                        "排隊等待",           # 報名狀態
                        "未聯繫",            # 聯繫狀態
                        date.today().strftime("%Y/%m/%d"), # 登記日期
                        n_name,
                        n_parent,
                        n_phone,
                        n_birth,
                        entry_info,         # 預計入學資訊
                        n_note,             # 備註
                        n_prio              # 重要性
                    ]
                    
                    try:
                        with st.spinner("正在寫入雲端..."):
                            sheet.append_row(new_row, value_input_option='USER_ENTERED')
                            st.success(f"🎉 {n_name if n_name else '新登記'} 錄入成功！")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"寫入失敗：{e}")
                else:
                    st.error("「電話」為必填項，請填寫後再送出。")

        st.divider()
        st.caption(f"📍 連動 ID：{GSHEET_ID[:10]}...")

if __name__ == "__main__":
    main()
