import streamlit as st
import json
import hashlib
import datetime
from urllib.parse import quote

# 頁面配置
st.set_page_config(page_title="HURC Token 預設格式驗證", layout="wide")

# 固定初始值
if 'ts' not in st.session_state:
    st.session_state.ts = "2026-02-13 10:09:36"

st.title("🛡️ 預設格式 Token 驗證器")
st.write("本工具使用 Python 預設的 `json.dumps()` (帶空格) 進行加密。")

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 參數設定")
    sys_val = st.text_input("SYSTEM 名稱", value="PMISHURC")
    # 注意：這裡我放了你提供的那個 Key
    key_val = st.text_input("INTEGRATE_TOKEN_KEY", value="PF$@GESA@F(#!QG_@G@!_^%^C")
    
    st.divider()
    if st.button("🔄 同步現在時間"):
        st.session_state.ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

# --- 主畫面：手動輸入時間 ---
ts_input = st.text_input("請輸入時間戳記 (修改後按 Enter)", value=st.session_state.ts)
st.session_state.ts = ts_input

# --- 核心邏輯 ---
def generate_token(sys, ts, key):
    # 這是你提供的原始 def 邏輯
    data_dict = {'system': sys, 'time': ts, 'key': key}
    
    # 預設格式：有雙引號，冒號與逗號後有空格
    data_str = json.dumps(data_dict)
    
    m = hashlib.md5()
    m.update(data_str.encode('utf-8'))
    sign = m.hexdigest().lower()
    
    return data_str, sign

# 執行計算
raw_data, final_token = generate_token(sys_val, ts_input, key_val)

# --- 結果呈現 ---
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 加密前字串 (Data)")
    st.info("請檢查此字串與伺服器端要求是否完全一致：")
    st.code(raw_data, language="json")
    
    st.subheader("🔑 產出的 Token (Sign)")
    st.success(f"**{final_token}**")

with col2:
    st.subheader("💡 驗證備忘錄")
    st.write("如果你輸入：")
    st.write(f"- System: `PMISHURC` \n- Time: `2026-02-13 10:09:36` \n- Key: `PF$@GESA@F(#!QG_@G@!_^%^C`")
    st.write("則 Token 應該是：")
    st.code("470878e36485882672be9c3132e08e6f")

# --- 網址預覽 ---
st.divider()
st.subheader("🔗 最終請求 URL 預覽")
encoded_ts = quote(ts_input, safe="")
final_url = f"http://john.yilanlun.com:8000/rcm/api/v1/.../?system={sys_val}&timestamp={encoded_ts}&token={final_token}"
st.code(final_url, language="text")
