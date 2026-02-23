import streamlit as st
import json
import hashlib
import datetime
from urllib.parse import quote

# 頁面配置
st.set_page_config(page_title="Token 嚴格對帳工具", layout="wide")

st.title("🛡️ API Token 格式驗證工具")
st.write("如果你算出來的 Token 跟別人不一樣，通常是「空格」在作怪。")

# --- 鎖定初始值，避免 Enter 重置 ---
if 'ts' not in st.session_state:
    st.session_state.ts = "2026-02-13 10:09:36"

# --- 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 設定參數")
    sys_val = st.text_input("SYSTEM 名稱", value="PMISHURC")
    key_val = st.text_input("INTEGRATE_TOKEN_KEY", value="PF$@GESA@F(#!QG_@G@!_^%^C")
    
    st.divider()
    if st.button("⏱️ 重設為目前時間"):
        st.session_state.ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

# --- 主畫面輸入 ---
ts_input = st.text_input("請輸入時間戳記 (Timestamp)", value=st.session_state.ts)
st.session_state.ts = ts_input

# --- 核心邏輯：兩種格式對照 ---
def calculate_tokens(system, timestamp, key):
    data_dict = {'system': system, 'time': timestamp, 'key': key}
    
    # 1. 預設格式 (有空格)
    json_standard = json.dumps(data_dict)
    token_standard = hashlib.md5(json_standard.encode('utf-8')).hexdigest().lower()
    
    # 2. 緊湊格式 (無空格) -> 這是算出 2c92... 的關鍵！
    json_compact = json.dumps(data_dict, separators=(',', ':'))
    token_compact = hashlib.md5(json_compact.encode('utf-8')).hexdigest().lower()
    
    return (json_standard, token_standard), (json_compact, token_compact)

(standard_json, standard_tk), (compact_json, compact_tk) = calculate_tokens(sys_val, ts_input, key_val)

# --- 結果呈現 ---
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("❌ 預設格式 (可能有誤)")
    st.write("`json.dumps` 預設會在冒號後加空格")
    st.code(standard_json, language="json")
    st.error(f"Token: `{standard_tk}`")
    if standard_tk == "470878e36485882672be9c3132e08e6f":
        st.caption("⚠️ 這是你之前算出的版本")

with col2:
    st.subheader("✅ 緊湊格式 (正確答案)")
    st.write("使用 `separators=(',', ':')` 消除空格")
    st.code(compact_json, language="json")
    st.success(f"Token: `{compact_tk}`")
    if compact_tk == "2c92d907303922ca37f6ccbea2c8a011":
        st.balloons()
        st.write("🎉 **這就是你要的答案！**")

# --- 產出網址 ---
st.divider()
st.subheader("🔗 最終請求 URL (建議使用緊湊版 Token)")
encoded_ts = quote(ts_input, safe="")
final_url = f"http://john.yilanlun.com:8000/rcm/api/v1/.../?system={sys_val}&timestamp={encoded_ts}&token={compact_tk}"
st.code(final_url, language="text")

with st.expander("💡 為什麼要用緊湊格式？"):
    st.write("""
    1. **跨語言相容性**：不同語言（PHP, Java, Node.js）對 JSON 字串中「空格」的處理規則不同。
    2. **標準化**：為了讓 MD5 的結果在任何地方都一樣，API 通常會要求在加密前『擠掉』所有不必要的空白。
    3. **你的程式碼修改建議**：
    """)
    st.code("""
# 請將原有的這行：
data = json.dumps({'system': system, 'time': timestamp, 'key': key})

# 修改為這行：
data = json.dumps({'system': system, 'time': timestamp, 'key': key}, separators=(',', ':'))
    """, language="python")
