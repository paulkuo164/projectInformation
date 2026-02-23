import streamlit as st
import json
import hashlib
import datetime
import requests
import pandas as pd
from urllib.parse import quote

# 頁面配置
st.set_page_config(page_title="HURC 專案進度儀表板", layout="wide", page_icon="🏗️")

# --- 核心加密函數：嚴格遵守預設格式 (帶空格) ---
def generate_integrate_token(system, timestamp, key):
    """
    完全依照你提供的邏輯：
    1. json.dumps 預設產生雙引號 + 冒號後空格
    2. utf-8 編碼
    3. md5 小寫輸出
    """
    data = json.dumps({'system': system, 'time': timestamp, 'key': key})
    m = hashlib.md5()
    m.update(data.encode('utf-8'))
    return m.hexdigest().lower()

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 系統驗證參數")
    host = st.text_input("HOST (系統網址)", value="http://john.yilanlun.com:8000")
    system_val = st.text_input("SYSTEM 名稱", value="PMISHURC")
    token_key = st.text_input("TOKEN KEY (金鑰)", value="PF$@GESA@F(#!QG_@G@!_^%^C", type="password")
    project_id = st.text_input("PROJECT ID (案號)", value="214")
    
    st.divider()
    st.subheader("🕒 時間控制")
    # 預設抓現在時間，但允許手動調整
    if 'manual_ts' not in st.session_state:
        st.session_state.manual_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    current_ts = st.text_input("使用時間戳記", value=st.session_state.manual_ts)
    st.session_state.manual_ts = current_ts # 鎖定手動輸入值

    if st.button("🔄 同步目前電腦時間"):
        st.session_state.manual_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

# --- API 請求函數 ---
def fetch_pmis_data(api_type, host, sys, ts, key, pid):
    clean_host = host.rstrip("/")
    token = generate_integrate_token(sys, ts, key)
    ts_encoded = quote(ts, safe="")
    
    if api_type == "info":
        url = f"{clean_host}/rcm/api/v1/projectinfoapi/{pid}/?system={sys}&timestamp={ts_encoded}&token={token}"
    else:
        url = f"{clean_host}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={pid}&system={sys}&timestamp={ts_encoded}&token={token}"
    
    try:
        resp = requests.get(url, timeout=10, verify=False)
        return resp.status_code, resp.json() if resp.status_code == 200 else None, url, token
    except Exception as e:
        return 999, None, url, token

# --- 主畫面標題 ---
st.title("🏗️ HURC 專案資訊與進度儀表板")
st.caption(f"目前連線至：{host} | 加密基準時間：{current_ts}")

if st.button("🚀 執行數據同步", use_container_width=True):
    with st.spinner("正在驗證 Token 並抓取資料..."):
        # 同步抓取兩份資料
        info_code, info_data, info_url, info_token = fetch_pmis_data("info", host, system_val, current_ts, token_key, project_id)
        prog_code, prog_data, prog_url, prog_token = fetch_pmis_data("prog", host, system_val, current_ts, token_key, project_id)
        
        tab1, tab2, tab3 = st.tabs(["📊 施工進度分析", "📋 專案基本資料", "🛠️ 系統診斷"])

        # --- Tab 1: 施工進度 ---
        with tab1:
            if prog_data and 'mix_data' in prog_data:
                st.success("✅ 進度數據同步成功")
                df = pd.DataFrame(prog_data['mix_data'])
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')

                # 指標看板
                last_record = df.iloc[-1]
                c1, c2, c3 = st.columns(3)
                c1.metric("實際進度", f"{last_record['act']}%")
                c2.metric("預計進度", f"{last_record['sch']}%")
                diff = round(last_record['act'] - last_record['sch'], 2)
                c3.metric("進度落後/超前", f"{diff}%", delta=diff)

                # S-Curve 圖表
                st.subheader("📈 施工進度 S-Curve")
                chart_df = df.rename(columns={'act': '實際實際', 'sch': '預定進度'}).set_index('date')
                st.line_chart(chart_df[['實際實際', '預定進度']])
                
                with st.expander("查看完整歷史數據"):
                    st.dataframe(df, use_container_width=True)
            else:
                st.error(f"❌ 進度資料抓取失敗 (代碼: {prog_code})")
                st.warning("請檢查 PROJECT ID 是否正確，或 Token 是否過期。")

        # --- Tab 2: 基本資料 ---
        with tab2:
            if info_data:
                st.success("✅ 專案資訊獲取成功")
                st.json(info_data)
            else:
                st.error(f"❌ 無法取得基本資料 (代碼: {info_code})")

        # --- Tab 3: 系統診斷 ---
        with tab3:
            st.subheader("🔍 加密驗證資訊")
            st.write(f"**使用的時間戳記:** `{current_ts}`")
            st.write(f"**產出的 Token:** `{prog_token}`")
            
            st.divider()
            st.write("**實際請求 URL (可複製至瀏覽器測試):**")
            st.code(prog_url, language="text")
            
            st.info("""
            **排錯小技巧：**
            1. 將上方 URL 貼到瀏覽器，若出現 403 代表 Token 錯誤。
            2. 檢查 Token Key 結尾是否有空格或少打字母。
            3. 若顯示 404，代表 API 路徑在該伺服器上不存在。
            """)

# 頁尾
st.divider()
st.caption("系統開發：Streamlit x HURC Integration Tool")
