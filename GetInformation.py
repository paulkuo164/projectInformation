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
    st.subheader("🕒 時間與延遲調整")
    
    # 選擇基礎時間
    if 'base_ts' not in st.session_state:
        st.session_state.base_ts = datetime.datetime.now()

    if st.button("🔄 抓取現在電腦時間"):
        st.session_state.base_ts = datetime.datetime.now()
        st.rerun()

    # 時間偏移量 (秒)
    time_offset = st.slider("時間偏移 (秒)", min_value=-300, max_value=300, value=0, help="正數代表增加秒數，負數代表延遲/減少秒數")
    
    # 計算最終使用的 Timestamp
    final_dt = st.session_state.base_ts + datetime.timedelta(seconds=time_offset)
    input_ts = final_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    st.write(f"**最終驗證時間:**")
    st.code(input_ts)

# --- 主畫面：第一步 - 驗證 Token ---
st.title("🏗️ HURC 數據同步工具 (含時差調校)")

# 先計算 Token 但不送出
raw_json, final_token = generate_token(system_val, input_ts, token_key)

st.header("第一步：檢查驗證資訊")
c1, c2 = st.columns([2, 1])

with c1:
    st.write("**擬傳送的加密字串 (Data):**")
    st.code(raw_json, language="json")
    st.caption(f"目前時間偏移：{time_offset} 秒")

with c2:
    st.write("**生成的 Token (MD5):**")
    st.success(f"`{final_token}`")

# 這裡顯示最終 URL 預覽
ts_encoded = quote(input_ts, safe="")
preview_url = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"

with st.expander("🔍 預覽完整請求網址"):
    st.code(preview_url, language="text")

st.divider()

# --- 主畫面：第二步 - 發送連線 ---
st.header("第二步：發送請求")

if st.button("🚀 確認無誤，發送 API 請求", use_container_width=True):
    with st.spinner("連線中..."):
        try:
            resp = requests.get(preview_url, timeout=10, verify=False)
            
            if resp.status_code == 200:
                st.success("✅ 連線成功！")
                data = resp.json()
                st.json(data) # 這裡先簡單展示回傳結果
                    
            elif resp.status_code == 401:
                st.error("❌ 錯誤 401：未經授權。")
                st.write("這通常代表 Token 或 Timestamp 驗證失敗。")
                st.info(f"伺服器回應：{resp.text}")
                
                # 自動診斷
                st.subheader("💡 排除建議")
                st.write("1. 嘗試調整側邊欄的 **『時間偏移』** (加減 1~2 分鐘)，看看是否為時差問題。")
                st.write("2. 檢查加密字串中的 `key` 是否包含不可見字元。")
            else:
                st.error(f"❌ 錯誤代碼：{resp.status_code}")
                st.write(resp.text)
                
        except Exception as e:
            st.error(f"⚡ 連線異常：{str(e)}")

# 頁尾
st.divider()
st.caption("Debug Info: MD5(JSON with spaces) logic applied.")
