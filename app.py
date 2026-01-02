import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
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
    .stMetric {
        background-color: white; padding: 24px; border-radius: 24px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03); border: 1px solid rgba(0,0,0,0.05);
    }
    .stButton>button {
        border-radius: 14px; font-weight: 700; border: none;
        background-color: #007AFF; color: white; transition: all 0.2s;
    }
    div[data-testid="stDataEditor"] {
        border-radius: 24px !important; overflow: hidden;
    }
    [data-testid="stSidebar"] { background-color: white; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 雲端連線配置 (精準鎖定 11 欄標題)
# ==========================================

GSHEET_ID = "1ZofZnB8Btig_6XvsHGh7bbapnfJM-vDkXTFpaU7ngmE"

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

# 嚴格定義的物理標題順序 (絕對不可更改)
COLS = ["報名狀態", "聯繫狀態", "登記日期", "幼兒姓名", "家長稱呼", "電話", "幼兒生日", "預計入學資訊", "推薦人", "備註", "重要性"]

@st.cache_resource
def get_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_JSON_KEY, scope)
    return gspread.authorize(creds)

def fetch_data():
    try:
        client = get_client()
        sheet = client.open_by_key(GSHEET_ID).get_sheets()[0]
        # 使用 get_all_values 讀取最原始的格子數據
        raw_data = sheet.get_all_values()
        
        if not raw_data:
            # 如果是全空的，立刻建立標題
            sheet.update(range_name='A1', values=[COLS])
            return pd.DataFrame(columns=COLS), sheet
        
        # 標題清理並建立 DataFrame
        headers = [str(h).strip() for h in raw_data[0]]
        df = pd.DataFrame(raw_data[1:], columns=headers)
        
        # 補齊缺失欄位並過濾，強制讓 DataFrame 的欄位順序 = COLS
        for col in COLS:
            if col not in df.columns:
                df[col] = ""
        
        return df[COLS].fillna(""), sheet
    except Exception as e:
        st.error(f"❌ 無法讀取 Excel 資料：{e}")
        return pd.DataFrame(), None

# ==========================================
# 2. 自動推算班別
# ==========================================
def calculate_grade(birthday_str):
    if not birthday_str or "/" not in str(birthday_str): return ""
    try:
        parts = str(birthday_str).split('/')
        roc_year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        ce_year = roc_year + 1911
        today = date.today()
        # 台灣開學基準點 (以此學年 9/1 為準)
        target_year = today.year if today.month < 9 else today.year + 1
        age = target_year - ce_year
        if month > 9 or (month == 9 and day >= 2): age -= 1
        grade_map = {2: "幼幼班", 3: "小班", 4: "中班", 5: "大班"}
        return f"{target_year - 1911}學年-{grade_map.get(age, f'{age}歲')}"
    except: return ""

# ==========================================
# 3. 主介面 UI
# ==========================================
def main():
    # 讀取最新數據
    df, sheet = fetch_data()
    
    t1, t2 = st.columns([5, 1])
    with t1:
        st.title("🏫 幼兒園招生雲端管理系統")
        st.caption("✅ 物理鎖定版：確保 11 欄位絕對不跑位")
    with t2:
        if st.button("🔄 刷新名單", use_container_width=True): 
            st.cache_resource.clear()
            st.rerun()

    # 數據看板
    if not df.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("總人數", len(df))
        m2.metric("待聯絡", len(df[df["聯繫狀態"].isin(["未聯繫", "待聯絡", ""])]))
        m3.metric("排隊中", len(df[df["報名狀態"].str.contains("排隊", na=False)]))
        m4.metric("連線", "雲端正常")

    st.divider()

    # 搜尋
    search = st.text_input("🔍 搜尋 (姓名、電話、推薦人、備註...)", placeholder="輸入關鍵字")
    display_df = df.copy()
    if search:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
        display_df = display_df[mask]

    # 表格區
    if not display_df.empty:
        st.subheader("📋 招生名單明細")
        
        # 強制在此鎖定欄位顯示順序
        updated_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "報名狀態": st.column_config.SelectboxColumn(options=["排隊等待", "已入學", "取消報名", "候補中"]),
                "聯繫狀態": st.column_config.SelectboxColumn(options=["未聯繫", "聯繫中", "已聯繫", "電話未接"]),
                "幼兒姓名": st.column_config.TextColumn(required=True),
                "備註": st.column_config.TextColumn(width="large"),
                "重要性": st.column_config.SelectboxColumn(options=["高", "中", "低"]),
                "預計入學資訊": st.column_config.TextColumn("推算分班"),
                "登記日期": st.column_config.TextColumn(disabled=True)
            }
        )
        
        # 同步儲存按鈕
        if st.button("💾 儲存所有修改至雲端 Excel", type="primary"):
            try:
                with st.spinner("同步中，請勿關閉視窗..."):
                    # 關鍵步驟：存檔前再次確保欄位順序與標題列完全一致
                    final_save_df = updated_df[COLS].fillna("").astype(str)
                    
                    # 徹底清除舊資料並寫入新資料 (包含標題)
                    sheet.clear()
                    sheet.update(range_name='A1', values=[COLS] + final_save_df.values.tolist(), value_input_option='USER_ENTERED')
                    
                    st.success("✅ 同步成功！雲端 Excel 已精準更新。")
                    time.sleep(1)
                    st.cache_resource.clear()
                    st.rerun()
            except Exception as e:
                st.error(f"儲存失敗：{e}")

    # 側邊欄：新增
    with st.sidebar:
        st.header("⚙️ 診斷與新增")
        if sheet:
            with st.expander("🔍 檢查雲端標題順序"):
                st.write(sheet.get_all_values()[0])
        
        st.divider()
        with st.form("add_form", clear_on_submit=True):
            n_name = st.text_input("孩子姓名")
            n_parent = st.text_input("家長稱呼")
            n_phone = st.text_input("電話*")
            n_birth = st.text_input("生日 (例 112/01/01)")
            n_ref = st.text_input("推薦人")
            n_note = st.text_area("備註")
            
            if st.form_submit_button("立即錄入雲端", use_container_width=True):
                if n_phone and sheet:
                    entry_info = calculate_grade(n_birth)
                    # 嚴格依照 11 個定錨位置排序
                    new_row = [
                        "排隊等待", "未聯繫", date.today().strftime("%Y/%m/%d"), 
                        n_name, n_parent, n_phone, n_birth, entry_info, n_ref, n_note, "中"
                    ]
                    try:
                        sheet.append_row(new_row, value_input_option='USER_ENTERED')
                        st.success(f"🎉 {n_name} 已成功存入！")
                        time.sleep(1)
                        st.cache_resource.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"寫入失敗：{e}")
                else:
                    st.error("電話為必填欄位")

if __name__ == "__main__":
    main()
