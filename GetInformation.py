import streamlit as st
import json
import hashlib
import datetime
import requests
from urllib.parse import quote

st.set_page_config(page_title="HURC API 診斷工具", layout="wide")

# --- 第一部分：IP 診斷 ---
st.header("🌐 環境診斷 (IP Check)")
try:
    # 透過外部服務取得目前 Streamlit 執行環境的公網 IP
    public_ip = requests.get('https://api64.ipify.org?format=json', timeout=5).json()['ip']
    st.info(f"目前 Streamlit Cloud 的出口 IP 為: **{public_ip}**")
    st.caption("💡 如果這個 IP 不在貴單位的白名單內，API 連線將會失敗。")
except Exception as e:
    st.error(f"無法取得目前 IP: {e}")

st.divider()

# --- 第二部分：API 測試邏輯 ---
st.header("🚀 API 連線測試")

with st.sidebar:
    st.subheader("參數設定")
    HOST = st.text_input("HOST", value="https://pmis.hurc.org.tw")
    SYSTEM = st.text_input("SYSTEM 名稱")
    TOKEN_KEY = st.text_input("TOKEN KEY", type="password")
    PROJECT_ID = st.text_input("PROJECT ID", value="214")

def generate_token(sys, ts, key):
    # 這裡使用最緊湊的格式，這是大多數 API 的標準
    data = json.dumps({"system": sys, "time": ts, "key": key}, separators=(',', ':'))
    m = hashlib.md5()
    m.update(data.encode("utf-8"))
    return m.hexdigest().lower(), data

if st.button("執行 API 測試"):
    if not SYSTEM or not TOKEN_KEY:
        st.warning("請填寫 SYSTEM 與 TOKEN KEY")
    else:
        now = datetime.datetime.now()
        found = False
        
        # 建立日誌容器
        log_container = st.container()
        
        for delta in range(0, 6):
            ts = now - datetime.timedelta(minutes=delta)
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            token, raw_str = generate_token(SYSTEM, ts_str, TOKEN_KEY)
            ts_encoded = quote(ts_str, safe="")
            url = f"{HOST}/rcm/api/v1/projectinfoapi/{PROJECT_ID}/?system={SYSTEM}&timestamp={ts_encoded}&token={token}"
            
            try:
                # 這裡增加 timeout 並關閉 verify 測試
                resp = requests.get(url, timeout=5, verify=False)
                
                with st.expander(f"測試時間 {ts_str} - 狀態碼: {resp.status_code}"):
                    st.write(f"**Request URL:** `{url}`")
                    st.write(f"**MD5 Payload:** `{raw_str}`")
                    
                    if resp.status_code == 200:
                        st.success("✅ 連線成功！")
                        st.json(resp.text)
                        found = True
                        break
                    else:
                        st.error(f"連線失敗，伺服器回傳：{resp.text}")
                        
            except requests.exceptions.ConnectTimeout:
                st.error(f"❌ 時間 {ts_str}: **連線逾時 (Timeout)**。這通常代表 IP 被防火牆擋住，封包進不去。")
            except Exception as e:
                st.error(f"❌ 發生錯誤: {e}")
                
        if not found:
            st.error("🏁 測試結束：未能成功取得資料。")
