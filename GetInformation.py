import streamlit as st
import json
import hashlib
import datetime
import requests
from urllib.parse import quote

# 設定網頁標題
st.set_page_config(page_title="PMIS API 測試工具", layout="wide")
st.title("🚀 HURC PMIS API 呼叫工具")

# --- 側邊欄配置 ---
with st.sidebar:
    st.header("API 參數設定")
    host = st.text_input("HOST", value="https://pmis.hurc.org.tw")
    system_val = st.text_input("SYSTEM 名稱", value="")
    token_key = st.text_input("TOKEN KEY", value="", type="password")
    project_id = st.text_input("PROJECT ID", value="214")
    timeout = st.slider("逾時設定 (秒)", 5, 30, 10)

# --- 核心邏輯函數 ---
def generate_integrate_token(system, timestamp, key):
    data = json.dumps({"system": system, "time": timestamp, "key": key})
    m = hashlib.md5()
    m.update(data.encode("utf-8"))
    return m.hexdigest().lower()

# --- 主畫面 UI ---
col1, col2 = st.columns([1, 1])

if st.button("開始獲取資料"):
    now = datetime.datetime.now()
    found_success = False
    
    st.info(f"正在嘗試從 {now.strftime('%H:%M:%S')} 往前回推 5 分鐘的驗證標籤...")
    
    # 建立一個進度條
    progress_bar = st.progress(0)
    
    for i, delta_min in enumerate(range(0, 6)):
        ts = now - datetime.timedelta(minutes=delta_min)
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        
        token = generate_integrate_token(system_val, ts_str, token_key)
        ts_encoded = quote(ts_str, safe="")
        url = f"{host}/rcm/api/v1/projectinfoapi/{project_id}/?system={system_val}&timestamp={ts_encoded}&token={token}"
        
        # 更新進度條
        progress_bar.progress((i + 1) / 6)
        
        try:
            resp = requests.get(url, timeout=timeout, verify=True)
            
            if resp.status_code == 200:
                st.success(f"✅ 成功連線！使用時間戳：{ts_str}")
                
                # 顯示詳細結果
                with st.expander("查看請求詳情", expanded=False):
                    st.write(f"**URL:** {url}")
                    st.write(f"**Token:** {token}")
                
                # 嘗試解析 JSON 並顯示
                try:
                    result_json = resp.json()
                    st.subheader("📊 回傳數據")
                    st.json(result_json) # Streamlit 自動排版 JSON
                except:
                    st.subheader("📄 回傳本文")
                    st.code(resp.text)
                
                found_success = True
                break
            else:
                st.warning(f"嘗試 {ts_str} 失敗 (狀態碼: {resp.status_code})")
                
        except Exception as e:
            st.error(f"連線異常: {e}")
            break
            
    if not found_success:
        st.error("❌ 在 ±5 分鐘內均未取得 200 回應，請檢查參數或網路狀態。")