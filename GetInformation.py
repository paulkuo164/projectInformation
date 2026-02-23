import streamlit as st
import json
import hashlib
import datetime
from datetime import timedelta
import requests
import pandas as pd
from urllib.parse import quote

# 頁面配置
st.set_page_config(page_title="HURC 數據同步工具", layout="wide")

# --- 核心加密函數 ---
def generate_token(system, timestamp, key):
    data_dict = {'system': system, 'time': timestamp, 'key': key}
    data_str = json.dumps(data_dict)
    m = hashlib.md5()
    m.update(data_str.encode('utf-8'))
    return data_str, m.hexdigest().lower()

# --- 側邊欄 ---
with st.sidebar:
    st.header("🔑 系統參數")
    host = st.text_input("HOST", value="http://john.yilanlun.com:8000")
    system_val = st.text_input("SYSTEM 名稱", value="PMISHURC")
    token_key = st.text_input("TOKEN KEY", value="PF$@GESA@F(#!QG_@G@!_^%^C", type="password")
    project_id = st.text_input("PROJECT ID", value="214")
    
    st.divider()
    st.subheader("🇹🇼 台灣時間設定")
    if 'current_ts' not in st.session_state:
        st.session_state.current_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    edited_ts = st.text_input("驗證時間 (TIMESTAMP)", value=st.session_state.current_ts)
    st.session_state.current_ts = edited_ts
    
    query_date = st.text_input("查詢日期 (DATE)", value=edited_ts.split(" ")[0])

    if st.button("🕒 同步台灣目前時間"):
        st.session_state.current_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

# --- 主畫面 ---
st.title("🏗️ HURC 工程數據監測")

raw_json, final_token = generate_token(system_val, edited_ts, token_key)
ts_encoded = quote(edited_ts, safe="")

if st.button("🚀 執行全面同步", use_container_width=True):
    url_a = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    url_b = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_type_progress/?project_id={project_id}&date={query_date}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    
    with st.spinner("連線中..."):
        try:
            resp_a = requests.get(url_a, timeout=10, verify=False)
            resp_b = requests.get(url_b, timeout=10, verify=False)
            
            tab1, tab2, tab3 = st.tabs(["📋 分項進度", "📈 總進度曲線", "🛠️ 系統診斷"])
            
            # --- Tab 1: 分項進度 (加上欄位檢查) ---
            with tab1:
                st.subheader(f"分項進度數據 ({query_date})")
                if resp_b.status_code == 200:
                    json_data_b = resp_b.json()
                    
                    if isinstance(json_data_b, list) and len(json_data_b) > 0:
                        df_type = pd.DataFrame(json_data_b)
                        
                        # 🔍 檢查必要欄位是否存在
                        required_cols = ['name', 'done_on_time', 'delayed']
                        existing_cols = [c for c in required_cols if c in df_type.columns]
                        
                        if 'delayed' in df_type.columns:
                            # 只有在有 'delayed' 欄位時才做高亮
                            st.dataframe(df_type.style.highlight_max(axis=0, subset=['delayed'], color='#FFCCCC'), use_container_width=True)
                            
                            st.subheader("⚠️ 分項落後趨勢")
                            # 只有在有 'name' 和 'delayed' 時才畫圖
                            if 'name' in df_type.columns:
                                st.bar_chart(df_type.set_index('name')['delayed'])
                        else:
                            # 如果沒有 delayed 欄位，僅顯示原始資料
                            st.warning("提醒：回傳資料中不包含 'delayed' 欄位，顯示原始表格。")
                            st.dataframe(df_type, use_container_width=True)
                    else:
                        st.info("💡 該日期回傳資料為空，請確認該日是否有填寫日報。")
                else:
                    st.error(f"分項進度請求失敗：{resp_b.status_code}")

            # --- Tab 2: 總進度 ---
            with tab2:
                if resp_a.status_code == 200:
                    prog_data = resp_a.json()
                    if 'mix_data' in prog_data and len(prog_data['mix_data']) > 0:
                        df_prog = pd.DataFrame(prog_data['mix_data'])
                        if 'date' in df_prog.columns:
                            df_prog['date'] = pd.to_datetime(df_prog['date'])
                            st.line_chart(df_prog.set_index('date')[['act', 'sch']])
                    else:
                        st.info("暫無總進度歷史資料。")

            # --- Tab 3: 診斷 ---
            with tab3:
                st.write("**API B 回傳原始內容：**")
                st.json(resp_b.json() if resp_b.status_code == 200 else {"status": "error"})
                st.write("**分項進度 URL:**")
                st.code(url_b)

        except Exception as e:
            st.error(f"連線異常：{str(e)}")
