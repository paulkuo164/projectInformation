import streamlit as st
import json
import hashlib
import datetime
from datetime import timedelta, timezone
import requests
import pandas as pd
from urllib.parse import quote

# 頁面配置
st.set_page_config(page_title="HURC 台灣時區儀表板", layout="wide")

# --- 核心加密函數 ---
def generate_token(system, timestamp, key):
    data_dict = {'system': system, 'time': timestamp, 'key': key}
    data_str = json.dumps(data_dict)
    m = hashlib.md5()
    m.update(data_str.encode('utf-8'))
    return data_str, m.hexdigest().lower()

# --- 取得台灣時間的函數 ---
def get_tw_now():
    # 取得當前 UTC 時間，並強制加上 8 小時
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    tw_now = utc_now + datetime.timedelta(hours=8)
    return tw_now.strftime("%Y-%m-%d %H:%M:%S")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 系統參數")
    host = st.text_input("HOST", value="http://john.yilanlun.com:8000")
    system_val = st.text_input("SYSTEM 名稱", value="PMISHURC")
    token_key = st.text_input("TOKEN KEY", value="PF$@GESA@F(#!QG_@G@!_^%^C", type="password")
    project_id = st.text_input("PROJECT ID", value="214")
    
    st.divider()
    st.subheader("🇹🇼 台灣時間控制 (UTC+8)")
    
    # 初始化：直接呼叫 +8 函數
    if 'current_ts' not in st.session_state:
        st.session_state.current_ts = get_tw_now()

    # TIMESTAMP 編輯框
    edited_ts = st.text_input("驗證時間戳記 (TIMESTAMP)", value=st.session_state.current_ts)
    st.session_state.current_ts = edited_ts
    
    # DATE 查詢日期 (預設連動 TIMESTAMP 的日期)
    default_date = edited_ts.split(" ")[0]
    query_date = st.text_input("查詢日期 (DATE)", value=default_date)

    if st.button("🕒 同步台灣目前時間 (+8)"):
        st.session_state.current_ts = get_tw_now()
        st.rerun()

# --- 主畫面 ---
st.title("🏗️ HURC 工程數據監測")
st.info(f"🇹🇼 當前設定時間：`{edited_ts}` (已手動/自動校正為台灣 UTC+8)")

# 計算 Token
raw_json, final_token = generate_token(system_val, edited_ts, token_key)
ts_encoded = quote(edited_ts, safe="")

if st.button("🚀 執行全面同步", use_container_width=True):
    # 組合 API URLs
    url_prog = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    url_type = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_type_progress/?project_id={project_id}&date={query_date}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    url_file = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/storage_file_list/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    
    with st.spinner("正在抓取數據..."):
        try:
            resp_prog = requests.get(url_prog, timeout=10, verify=False)
            resp_type = requests.get(url_type, timeout=10, verify=False)
            resp_file = requests.get(url_file, timeout=10, verify=False)
            
            tab1, tab2, tab3, tab4 = st.tabs(["📂 檔案系統列表", "📋 分項進度", "📈 總進度曲線", "🛠️ 系統診斷"])
            
            # --- 各分頁邏輯 (加入欄位檢查以免錯誤) ---
            with tab1:
                if resp_file.status_code == 200:
                    st.dataframe(pd.DataFrame(resp_file.json()), use_container_width=True)
                else: st.error("檔案列表讀取失敗")

            with tab2:
                if resp_type.status_code == 200:
                    df_type = pd.DataFrame(resp_type.json())
                    if not df_type.empty and 'delayed' in df_type.columns:
                        st.dataframe(df_type, use_container_width=True)
                        st.bar_chart(df_type.set_index('name')['delayed'])
                    else: st.warning("該日期無分項進度。")

            with tab3:
                if resp_prog.status_code == 200:
                    p_data = resp_prog.json().get('mix_data', [])
                    if p_data:
                        df_p = pd.DataFrame(p_data)
                        df_p['date'] = pd.to_datetime(df_p['date'])
                        st.line_chart(df_p.set_index('date')[['act', 'sch']])

            with tab4:
                st.write("**加密基準字串:**")
                st.code(raw_json)
                st.write("**目前 Token:**", final_token)

        except Exception as e:
            st.error(f"連線異常：{str(e)}")

st.divider()
st.caption("時區校正已啟用：系統會自動將所有時間戳記補齊為台灣時間 (UTC+8)。")

# 記憶功能確認
st.write("好的，我會記住查詢時間（Timestamp）固定為台灣時區（UTC+8）。你隨時可以要求我忘掉內容，或管理儲存在[設定](https://gemini.google.com/saved-info)裡的資訊。")

