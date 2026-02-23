import streamlit as st
import json
import hashlib
import datetime
import requests
import pandas as pd
from urllib.parse import quote

# 頁面配置
st.set_page_config(page_title="HURC 驗證儀表板", layout="wide")

# --- 核心加密函數 (預設格式：有空格) ---
def generate_token(system, timestamp, key):
    data_dict = {'system': system, 'time': timestamp, 'key': key}
    data_str = json.dumps(data_dict) # 產生帶空格的雙引號 JSON
    m = hashlib.md5()
    m.update(data_str.encode('utf-8'))
    return data_str, m.hexdigest().lower()

# --- 側邊欄：參數輸入 ---
with st.sidebar:
    st.header("🔑 認證參數設定")
    host = st.text_input("HOST", value="http://john.yilanlun.com:8000")
    system_val = st.text_input("SYSTEM 名稱", value="PMISHURC")
    token_key = st.text_input("TOKEN KEY", value="PF$@GESA@F(#!QG_@G@!_^%^C", type="password")
    project_id = st.text_input("PROJECT ID", value="214")
    
    st.divider()
    if 'ts_val' not in st.session_state:
        st.session_state.ts_val = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    input_ts = st.text_input("驗證時間戳記", value=st.session_state.ts_val)
    st.session_state.ts_val = input_ts

    if st.button("🔄 更新為現在時間"):
        st.session_state.ts_val = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

# --- 主畫面：第一步 - 驗證 Token ---
st.title("🏗️ HURC 數據同步工具")

# 先計算 Token 但不送出
raw_json, final_token = generate_token(system_val, input_ts, token_key)

st.header("第一步：檢查驗證資訊")
c1, c2 = st.columns([2, 1])

with c1:
    st.write("**擬傳送的加密字串 (Data):**")
    st.code(raw_json, language="json")

with c2:
    st.write("**生成的 Token (MD5):**")
    st.success(f"`{final_token}`")

# 這裡顯示最終 URL 預覽，方便你手動測試
ts_encoded = quote(input_ts, safe="")
preview_url = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"

with st.expander("🔍 預覽完整請求網址"):
    st.code(preview_url, language="text")
    st.caption("你可以先複製此網址到瀏覽器測試，若出現 401 代表 Token 仍有誤。")

st.divider()

# --- 主畫面：第二步 - 發送連線 ---
st.header("第二步：發送請求")
st.warning("請確認上方 Token 無誤後，再點擊下方按鈕進行同步。")

if st.button("🚀 確認無誤，發送 API 請求", use_container_width=True):
    with st.spinner("連線中..."):
        try:
            # 這裡執行實際的 API 呼叫
            resp = requests.get(preview_url, timeout=10, verify=False)
            
            if resp.status_code == 200:
                st.success("✅ 連線成功！已取得資料。")
                data = resp.json()
                
                # 展示資料內容
                tab_prog, tab_raw = st.tabs(["📊 進度數據", "📄 原始 JSON"])
                
                with tab_prog:
                    if 'mix_data' in data:
                        df = pd.DataFrame(data['mix_data'])
                        st.dataframe(df, use_container_width=True)
                        # 畫一個簡單的圖
                        df['date'] = pd.to_datetime(df['date'])
                        st.line_chart(df.set_index('date')[['act', 'sch']])
                    else:
                        st.info("連線成功，但回傳資料中沒有進度明細。")
                
                with tab_raw:
                    st.json(data)
                    
            elif resp.status_code == 401:
                st.error("❌ 錯誤 401：未經授權。")
                st.write("這通常代表伺服器端算出的 Token 與你目前算出的不符。")
                st.info(f"伺服器回傳內容：{resp.text}")
            else:
                st.error(f"❌ 錯誤代碼：{resp.status_code}")
                st.write(resp.text)
                
        except Exception as e:
            st.error(f"⚡ 連線異常：{str(e)}")

# 頁尾
st.divider()
st.caption("建議：若持續 401，請檢查 Key 是否包含特殊字元導致編碼問題。")
