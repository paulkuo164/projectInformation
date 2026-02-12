import streamlit as st
import json
import hashlib
import datetime
import requests
from urllib.parse import quote
import time

# --- 頁面配置 ---
st.set_page_config(page_title="HURC API 偵錯工具", layout="wide")

st.title("🛠️ HURC PMIS API 整合測試工具")
st.markdown("""
此工具會自動嘗試當前時間 ±5 分鐘的 Token 驗證，解決伺服器與本機時間不一致導致的驗證失敗問題。
""")

# --- 側邊欄：參數設定 ---
with st.sidebar:
    st.header("🔑 憑證與設定")
    HOST = st.text_input("主機網址", value="https://pmis.hurc.org.tw")
    SYSTEM = st.text_input("系統名稱 (system)", value="")
    TOKEN_KEY = st.text_input("驗證金鑰 (token_key)", value="", type="password")
    PROJECT_ID = st.text_input("專案代碼 (project_id)", value="214")
    
    st.divider()
    st.header("⚙️ 進階選項")
    timeout_val = st.number_input("連線逾時(秒)", value=10)
    verify_ssl = st.checkbox("驗證 SSL 憑證", value=True)
    show_debug = st.checkbox("顯示除錯詳細資訊", value=True)

# --- 核心邏輯 ---
def generate_token(system, timestamp, key):
    # 注意：這裡的 JSON 格式（空格、順序）必須與後端完全一致
    payload_dict = {"system": system, "time": timestamp, "key": key}
    data = json.dumps(payload_dict, separators=(',', ':')) # 移除多餘空格以確保雜湊一致性
    
    m = hashlib.md5()
    m.update(data.encode("utf-8"))
    sign = m.hexdigest().lower()
    return sign, data

# --- 主介面佈局 ---
col_ctrl, col_res = st.columns([1, 2])

with col_ctrl:
    st.subheader("控制台")
    run_btn = st.button("🚀 開始測試連線", use_container_width=True)
    
    if run_btn:
        if not SYSTEM or not TOKEN_KEY:
            st.error("請先填寫 SYSTEM 與 TOKEN_KEY")
        else:
            now = datetime.datetime.now()
            st.write(f"🕒 本機時間: `{now.strftime('%Y-%m-%d %H:%M:%S')}`")
            
            success = False
            results_log = []
            
            progress_bar = st.progress(0)
            
            # 嘗試 ±5 分鐘（共 11 個時間點）
            for i, delta in enumerate(range(0, 6)):
                # 這裡目前僅實作往回推，若有需要可改為 range(-5, 6)
                ts = now - datetime.timedelta(minutes=delta)
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                
                # 生成 Token
                token, raw_json = generate_token(SYSTEM, ts_str, TOKEN_KEY)
                ts_encoded = quote(ts_str, safe="")
                url = f"{HOST}/rcm/api/v1/projectinfoapi/{PROJECT_ID}/?system={SYSTEM}&timestamp={ts_encoded}&token={token}"
                
                progress_bar.progress((i + 1) / 6)
                
                try:
                    resp = requests.get(url, timeout=timeout_val, verify=verify_ssl)
                    status_code = resp.status_code
                    
                    if status_code == 200:
                        success = True
                        st.balloons()
                        with col_res:
                            st.success(f"✅ 連線成功！ (時間點: {ts_str})")
                            st.subheader("📦 API 回傳數據")
                            try:
                                st.json(resp.json())
                            except:
                                st.text_area("回傳非 JSON 文字", value=resp.text, height=300)
                        break
                    else:
                        results_log.append({"時間": ts_str, "狀態碼": status_code, "訊息": "驗證失敗或無權限"})
                        
                except Exception as e:
                    st.error(f"連線發生錯誤: {str(e)}")
                    break
            
            if not success:
                st.error("❌ 所有時間點嘗試均失敗")
                with col_res:
                    st.warning("除錯建議：")
                    st.markdown("""
                    1. **檢查 Token 格式**：確認 JSON 字串中的 Key 順序是否正確。
                    2. **檢查網址**：確認 `PROJECT_ID` 是否存在。
                    3. **防火牆/IP**：確認您的 IP 是否在該 API 的允許清單內。
                    """)
                    if show_debug:
                        st.subheader("🔍 嘗試紀錄")
                        st.table(results_log)

else:
    with col_res:
        st.info("💡 請在左側輸入參數並按下「開始測試連線」。")
        # 這裡可以放一個示意圖說明 API 驗證流程
        #
