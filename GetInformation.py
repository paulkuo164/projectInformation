import streamlit as st
import json
import hashlib
import datetime
from datetime import timedelta
import requests
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from urllib.parse import quote
import io

# 頁面配置
st.set_page_config(page_title="HURC 數據監測整合版", layout="wide")

# --- 1. 核心函數 ---
def generate_token(system, timestamp, key):
    data_dict = {'system': system, 'time': timestamp, 'key': key}
    data_str = json.dumps(data_dict)
    m = hashlib.md5()
    m.update(data_str.encode('utf-8'))
    return data_str, m.hexdigest().lower()

def get_tw_now():
    # 強制校正為台灣 UTC+8
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    tw_now = utc_now + datetime.timedelta(hours=8)
    return tw_now.strftime("%Y-%m-%d %H:%M:%S")

# --- 2. 初始化 Session State (防止搜尋時資料消失) ---
if 'file_data' not in st.session_state:
    st.session_state.file_data = None
if 'type_data' not in st.session_state:
    st.session_state.type_data = None
if 'prog_data' not in st.session_state:
    st.session_state.prog_data = None

# --- 3. 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 系統參數")
    host = st.text_input("HOST", value="http://john.yilanlun.com:8000")
    system_val = st.text_input("SYSTEM", value="PMISHURC")
    token_key = st.text_input("TOKEN KEY", value="PF$@GESA@F(#!QG_@G@!_^%^C", type="password")
    project_id = st.text_input("PROJECT ID", value="214")
    
    st.divider()
    st.subheader("🇹🇼 台灣時間控制")
    if 'current_ts' not in st.session_state:
        st.session_state.current_ts = get_tw_now()

    edited_ts = st.text_input("驗證時間戳記", value=st.session_state.current_ts)
    query_date = st.text_input("查詢日期 (DATE)", value=edited_ts.split(" ")[0])

    if st.button("🕒 同步目前時間"):
        st.session_state.current_ts = get_tw_now()
        st.rerun()

# --- 4. 主畫面邏輯 ---
st.title("🏗️ HURC 工程數據監測儀表板")

# 計算 Token 與 編碼
raw_json, final_token = generate_token(system_val, edited_ts, token_key)
ts_encoded = quote(edited_ts, safe="")

# 同步按鈕
if st.button("🚀 執行全面同步", use_container_width=True):
    # API 網址組合
    url_prog = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    url_type = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_type_progress/?project_id={project_id}&date={query_date}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    url_file = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/storage_file_list/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    
    with st.spinner("正在抓取數據..."):
        try:
            requests.packages.urllib3.disable_warnings() # 消除 SSL 警告
            
            resp_file = requests.get(url_file, timeout=10, verify=False)
            resp_type = requests.get(url_type, timeout=10, verify=False)
            resp_prog = requests.get(url_prog, timeout=10, verify=False)
            
            # 將數據存入 Session State，這樣搜尋時才不會不見
            if resp_file.status_code == 200: st.session_state.file_data = resp_file.json()
            if resp_type.status_code == 200: st.session_state.type_data = resp_type.json()
            if resp_prog.status_code == 200: st.session_state.prog_data = resp_prog.json()
            
            st.success("數據同步完成！")
        except Exception as e:
            st.error(f"連線異常：{str(e)}")
# --- 5. 數據顯示區 (使用 Session State 數據) ---
    if st.session_state.file_data is not None:
        tab1, tab2, tab3, tab4 = st.tabs(["📂 檔案系統列表", "📋 分項進度", "📈 總進度曲線", "🛠️ 系統診斷"])
        
        with tab1:
            # 讀取資料
            df_raw = pd.DataFrame(st.session_state.file_data)
            
            # 強制處理欄位名稱：將 name 轉為 名稱, tags 轉為 標籤
            # 使用列表推導式與 rename 確保大小寫都能抓到
            rename_dict = {}
            for col in df_raw.columns:
                if col.lower() == 'name': rename_dict[col] = "名稱"
                if col.lower() == 'tags': rename_dict[col] = "標籤"
            
            df_display = df_raw.rename(columns=rename_dict)
            
            # 如果改名成功，只顯示我們要的欄位；否則顯示全部
            display_cols = [c for c in ["名稱", "標籤"] if c in df_display.columns]
            if display_cols:
                df_display = df_display[display_cols]

            if not df_display.empty:
                # 🔍 搜尋框
                search_query = st.text_input("🔍 搜尋檔案關鍵字", placeholder="輸入名稱或標籤...", key="file_search_input")
                
                if search_query:
                    mask = df_display.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
                    df_filtered = df_display[mask]
                    st.dataframe(df_filtered, use_container_width=True)
                else:
                    st.dataframe(df_display, use_container_width=True)
            else:
                st.warning("查無檔案數據。")

        with tab2:
            if st.session_state.type_data:
                df_type = pd.DataFrame(st.session_state.type_data)
                if not df_type.empty:
                    st.dataframe(df_type, use_container_width=True)
                    if 'delayed' in df_type.columns and 'name' in df_type.columns:
                        st.bar_chart(df_type.set_index('name')['delayed'])
                else:
                    st.warning("該日期無分項進度。")

        with tab3:
            if st.session_state.prog_data:
                p_data = st.session_state.prog_data.get('mix_data', [])
                if p_data:
                    df_p = pd.DataFrame(p_data)
                    df_p['date'] = pd.to_datetime(df_p['date'])
                    st.line_chart(df_p.set_index('date')[['act']])
                else:
                    st.warning("無進度數據。")

        with tab4:
            st.write("**加密基準 JSON:**")
            st.code(raw_json)
            st.write("**目前 Token:**", final_token)
else:
    st.info("💡 請點擊上方「執行全面同步」按鈕以開始載入數據。")

st.divider()
st.caption("時區校正：UTC+8 (Taipei) | 搜尋連動：已啟用 Session 緩存機制")




