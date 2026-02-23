import streamlit as st
import json
import hashlib
import datetime
import requests
import pandas as pd
from urllib.parse import quote

# 頁面配置
st.set_page_config(page_title="HURC 綜合監測儀表板", layout="wide")

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
    st.subheader("🇹🇼 台灣時間與日期")
    if 'current_ts' not in st.session_state:
        st.session_state.current_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 驗證用時間戳記 (手動編輯保持)
    edited_ts = st.text_input("驗證時間戳記 (TIMESTAMP)", value=st.session_state.current_ts)
    st.session_state.current_ts = edited_ts
    
    # 分項進度專用日期
    default_date = edited_ts.split(" ")[0]
    query_date = st.text_input("查詢日期 (DATE)", value=default_date)

    if st.button("🕒 同步台灣目前時間"):
        st.session_state.current_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

# --- 主畫面 ---
st.title("🏗️ HURC 工程數據監測綜合儀表板")
st.info(f"當前模式：台灣時區 (UTC+8) | 驗證時間：`{edited_ts}`")

# 預算 Token
raw_json, final_token = generate_token(system_val, edited_ts, token_key)
ts_encoded = quote(edited_ts, safe="")

# --- API 執行連線 ---
if st.button("🚀 執行全面同步 (包含檔案列表)", use_container_width=True):
    # API 清單
    # 1. 總進度
    url_prog = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    # 2. 分項進度
    url_type = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_type_progress/?project_id={project_id}&date={query_date}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    # 3. 檔案列表 (新加入)
    url_file = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/storage_file_list/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    
    with st.spinner("正在同步多項數據..."):
        try:
            resp_prog = requests.get(url_prog, timeout=10, verify=False)
            resp_type = requests.get(url_type, timeout=10, verify=False)
            resp_file = requests.get(url_file, timeout=10, verify=False)
            
            tab1, tab2, tab3, tab4 = st.tabs(["📂 檔案系統列表", "📋 分項進度", "📈 總進度曲線", "🛠️ 系統診斷"])
            
            # --- Tab 1: 檔案系統列表 ---
            with tab1:
                st.subheader("📁 專案關聯檔案清單")
                if resp_file.status_code == 200:
                    file_data = resp_file.json()
                    if file_data:
                        df_file = pd.DataFrame(file_data)
                        # 美化顯示
                        st.write(f"共計找到 {len(df_file)} 個檔案")
                        st.dataframe(df_file.rename(columns={'name': '檔案名稱', 'tags': '標籤分類'}), use_container_width=True)
                    else:
                        st.info("此專案目前無檔案紀錄。")
                else:
                    st.error(f"檔案列表抓取失敗 (Code: {resp_file.status_code})")

            # --- Tab 2: 分項進度 ---
            with tab2:
                st.subheader(f"分項進度報告 ({query_date})")
                if resp_type.status_code == 200:
                    type_data = resp_type.json()
                    if type_data:
                        df_type = pd.DataFrame(type_data)
                        st.dataframe(df_type.style.highlight_max(axis=0, subset=['delayed'], color='#FFCCCC'), use_container_width=True)
                        st.bar_chart(df_type.set_index('name')['delayed'])
                    else:
                        st.warning("查無此日期的分項資料。")
                else:
                    st.error(f"分項進度失敗: {resp_type.status_code}")

            # --- Tab 3: 總進度 ---
            with tab3:
                st.subheader("總進度 S-Curve")
                if resp_prog.status_code == 200:
                    p_data = resp_prog.json()
                    if 'mix_data' in p_data:
                        df_p = pd.DataFrame(p_data['mix_data'])
                        df_p['date'] = pd.to_datetime(df_p['date'])
                        st.line_chart(df_p.set_index('date')[['act', 'sch']])
                else:
                    st.error(f"總進度失敗: {resp_prog.status_code}")

            # --- Tab 4: 系統診斷 ---
            with tab4:
                st.write("**加密字串 (Raw JSON):**")
                st.code(raw_json, language="json")
                st.write(f"**Token:** `{final_token}`")
                st.divider()
                st.write("**檔案列表 API URL:**")
                st.code(url_file)

        except Exception as e:
            st.error(f"連線異常：{str(e)}")

st.divider()
st.caption("備註：檔案標籤 (Tags) 可能包含多個分類，請使用表格搜尋功能進行篩選。")
