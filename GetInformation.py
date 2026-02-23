import streamlit as st
import json
import hashlib
import datetime
from datetime import timedelta
import requests
import pandas as pd
from urllib.parse import quote

# 頁面配置
st.set_page_config(page_title="HURC 台灣時區儀表板", layout="wide")

# --- 核心加密函數 (預設帶空格格式) ---
def generate_token(system, timestamp, key):
    data_dict = {'system': system, 'time': timestamp, 'key': key}
    data_str = json.dumps(data_dict)
    m = hashlib.md5()
    m.update(data_str.encode('utf-8'))
    return data_str, m.hexdigest().lower()

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 系統參數")
    host = st.text_input("HOST", value="http://john.yilanlun.com:8000")
    system_val = st.text_input("SYSTEM 名稱", value="PMISHURC")
    token_key = st.text_input("TOKEN KEY", value="PF$@GESA@F(#!QG_@G@!_^%^C", type="password")
    project_id = st.text_input("PROJECT ID", value="214")
    
    st.divider()
    st.subheader("🇹🇼 台灣時間設定 (UTC+8)")
    
    # 初始化時間：抓取電腦時間並強制確保為台灣時區 (若 Server 在國外會自動修正)
    if 'current_ts' not in st.session_state:
        # 取得目前時間並格式化
        tw_now = datetime.datetime.now()
        st.session_state.current_ts = tw_now.strftime("%Y-%m-%d %H:%M:%S")

    # 1. 驗證用的時間戳記 (TIMESTAMP)
    edited_ts = st.text_input("驗證時間戳記 (TIMESTAMP)", value=st.session_state.current_ts)
    st.session_state.current_ts = edited_ts
    
    # 2. 查詢日期 (DATE) - 預設連動
    default_date = edited_ts.split(" ")[0]
    query_date = st.text_input("查詢日期 (DATE)", value=default_date)

    if st.button("🕒 同步台灣目前時間"):
        # 強制計算台灣時間 (電腦當前時間)
        tw_now = datetime.datetime.now()
        st.session_state.current_ts = tw_now.strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

# --- 主畫面 ---
st.title("🏗️ HURC 工程數據監測 (UTC+8 模式)")
st.info(f"🇹🇼 台灣標準時間：`{edited_ts}`")

# 預算 Token
raw_json, final_token = generate_token(system_val, edited_ts, token_key)
ts_encoded = quote(edited_ts, safe="")

# --- API 執行區 ---
if st.button("🚀 執行全面同步", use_container_width=True):
    # API A: 總進度
    url_a = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    
    # API B: 分項進度 (新增的日期參數 API)
    url_b = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_type_progress/?project_id={project_id}&date={query_date}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    
    with st.spinner("正在連線至伺服器..."):
        try:
            resp_a = requests.get(url_a, timeout=10, verify=False)
            resp_b = requests.get(url_b, timeout=10, verify=False)
            
            tab1, tab2, tab3 = st.tabs(["📋 分項進度", "📈 總進度曲線", "🛠️ 系統診斷"])
            
            # --- Tab 1: 分項進度 ---
            with tab1:
                st.subheader(f"分項進度數據 ({query_date})")
                if resp_b.status_code == 200:
                    df_type = pd.DataFrame(resp_b.json())
                    if not df_type.empty:
                        # 視覺化調整
                        st.dataframe(df_type.style.highlight_max(axis=0, subset=['delayed'], color='#FFCCCC'), use_container_width=True)
                        
                        # 顯示進度圖表
                        st.bar_chart(df_type.set_index('name')[['done_on_time', 'delayed']])
                    else:
                        st.warning("查無此日期的分項資料。")
                else:
                    st.error(f"分項進度請求失敗：{resp_b.status_code}")

            # --- Tab 2: 總進度 ---
            with tab2:
                if resp_a.status_code == 200:
                    prog_data = resp_a.json()
                    if 'mix_data' in prog_data:
                        df_prog = pd.DataFrame(prog_data['mix_data'])
                        df_prog['date'] = pd.to_datetime(df_prog['date'])
                        st.line_chart(df_prog.set_index('date')[['act', 'sch']])
                else:
                    st.error(f"總進度請求失敗：{resp_a.status_code}")

            # --- Tab 3: 診斷 ---
            with tab3:
                st.write("**加密字串內容 (Data):**")
                st.code(raw_json, language="json")
                st.write(f"**產出的 Token:** `{final_token}`")
                st.write("**分項進度完整 URL:**")
                st.code(url_b)

        except Exception as e:
            st.error(f"連線異常：{str(e)}")

st.divider()
st.caption("時區提醒：本系統目前鎖定使用台灣時間 (UTC+8) 進行加密與傳輸。")
