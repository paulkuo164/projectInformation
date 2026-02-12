import streamlit as st
import json
import hashlib
import datetime
import requests
from urllib.parse import quote

# 頁面基本設定
st.set_page_config(page_title="HURC API Debugger", layout="centered")
st.title("🏗️ HURC PMIS API 驗證測試器")

# --- 側邊欄輸入區 ---
with st.sidebar:
    st.header("1. 基礎參數設定")
    host = st.text_input("HOST", value="https://pmis.hurc.org.tw")
    system_name = st.text_input("SYSTEM 名稱", value="請輸入")
    token_key = st.text_input("TOKEN KEY", value="", type="password")
    project_id = st.text_input("PROJECT ID", value="214")
    
    st.divider()
    st.header("2. 加密格式微調")
    # 有些系統要求 JSON key 之間不能有空格，有些則要
    compact_json = st.checkbox("使用緊湊格式 JSON (無空格)", value=False)
    sort_keys = st.checkbox("依照字母順序排列 Key", value=False)

# --- 核心加密函數 ---
def generate_token(sys, ts, key, compact, sort):
    # 建構字典
    data_dict = {"system": sys, "time": ts, "key": key}
    
    # 根據設定決定序列化方式
    if compact:
        # 結果範例: {"system":"A","time":"B","key":"C"}
        raw_str = json.dumps(data_dict, separators=(',', ':'), sort_keys=sort)
    else:
        # 結果範例: {"system": "A", "time": "B", "key": "C"}
        raw_str = json.dumps(data_dict, sort_keys=sort)
        
    m = hashlib.md5()
    m.update(raw_str.encode("utf-8"))
    sign = m.hexdigest().lower()
    return sign, raw_str

# --- 主畫面操作 ---
if st.button("🔍 開始偵錯連線", use_container_width=True):
    if not token_key or system_name == "請輸入":
        st.warning("⚠️ 請填寫完整的 SYSTEM 與 TOKEN KEY")
    else:
        now = datetime.datetime.now()
        st.info(f"執行時間: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        found = False
        # 嘗試前後各 3 分鐘，覆蓋更大範圍
        for delta in range(-3, 4):
            ts = now + datetime.timedelta(minutes=delta)
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            
            token, debug_raw = generate_token(system_name, ts_str, token_key, compact_json, sort_keys)
            ts_encoded = quote(ts_str, safe="")
            test_url = f"{host}/rcm/api/v1/projectinfoapi/{project_id}/?system={system_name}&timestamp={ts_encoded}&token={token}"
            
            try:
                # 這裡關閉 verify 以防證書問題，但在正式環境建議開啟
                resp = requests.get(test_url, timeout=5, verify=False)
                
                # 顯示每一次嘗試的日誌 (展開式)
                with st.expander(f"嘗試時間: {ts_str} | 狀態: {resp.status_code}"):
                    st.code(f"URL: {test_url}")
                    st.write(f"**加密原始字串 (Payload):** `{debug_raw}`")
                    st.write(f"**生成的 MD5 Token:** `{token}`")
                    
                    if resp.status_code == 200:
                        st.success("🎉 成功取得資料！")
                        st.json(resp.text)
                        found = True
                        break
                    else:
                        st.error(f"失敗。伺服器回傳內容: {resp.text}")
                        
            except Exception as e:
                st.error(f"連線異常: {e}")
                break
        
        if not found:
            st.error("❌ 所有時間點均驗證失敗。")
            st.markdown("""
            ### 💡 排除故障建議：
            1. **檢查 Key 的順序**：嘗試勾選或取消「依照字母順序排列 Key」。
            2. **檢查 JSON 空格**：嘗試勾選或取消「使用緊湊格式」。
            3. **手動對時**：確認你的電腦時間與 [Time.is](https://time.is) 是否一致。
            4. **確認 SYSTEM 名稱**：有些系統對大小寫敏感。
            """)
            
