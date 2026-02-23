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
    data_str = json.dumps(data_dict)
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
    st.subheader("🕒 時間編輯與偏移")
    
    # 初始化時間
    if 'current_ts' not in st.session_state:
        st.session_state.current_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 完全手動編輯框
    edited_ts = st.text_input("手動編輯時間戳記", value=st.session_state.current_ts)
    
    # 2. 偏移按鈕 (提供快速增減秒數，不會重置整個框)
    st.write("微調偏移：")
    c_dec, c_inc = st.columns(2)
    if c_dec.button("➖ 減少 30 秒"):
        dt = datetime.datetime.strptime(edited_ts, "%Y-%m-%d %H:%M:%S") - datetime.timedelta(seconds=30)
        st.session_state.current_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()
    if c_inc.button("➕ 增加 30 秒"):
        dt = datetime.datetime.strptime(edited_ts, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(seconds=30)
        st.session_state.current_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

    if st.button("🕒 回復目前電腦時間"):
        st.session_state.current_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

# --- 主畫面 ---
st.title("🏗️ HURC 數據同步工具 (完全編輯版)")

# 使用最終確定的時間
final_ts = edited_ts
raw_json, final_token = generate_token(system_val, final_ts, token_key)

st.header("第一步：檢查驗證資訊")
col_a, col_b = st.columns([2, 1])

with col_a:
    st.write("**擬傳送的加密字串 (Data):**")
    st.code(raw_json, language="json")
    st.caption(f"當前設定時間：{final_ts}")

with col_b:
    st.write("**生成的 Token (MD5):**")
    st.success(f"`{final_token}`")

# 預覽網址
ts_encoded = quote(final_ts, safe="")
preview_url = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"

with st.expander("🔍 預覽完整請求網址"):
    st.code(preview_url, language="text")

st.divider()

# --- 發送連線 ---
st.header("第二步：發送請求")

if st.button("🚀 確認無誤，發送 API 請求", use_container_width=True):
    with st.spinner("連線中..."):
        try:
            resp = requests.get(preview_url, timeout=10, verify=False)
            
            if resp.status_code == 200:
                st.success("✅ 連線成功！")
                st.json(resp.json())
            elif resp.status_code == 401:
                st.error("❌ 錯誤 401：未經授權")
                st.info(f"伺服器回應訊息：{resp.text}")
                st.warning("提示：這通常代表 Token 與時間戳記不匹配。請嘗試手動修改秒數後再次執行。")
            else:
                st.error(f"❌ 錯誤代碼：{resp.status_code}")
                st.write(resp.text)
        except Exception as e:
            st.error(f"⚡ 連線異常：{str(e)}")

st.divider()
st.caption("提示：手動編輯時間後請按 Enter 鍵確認，然後再點擊發送請求。")
