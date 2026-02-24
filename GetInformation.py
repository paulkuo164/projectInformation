import streamlit as st
import json
import hashlib
import datetime
from datetime import timedelta
import requests
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from urllib.parse import quote
import io

# --- 1. 核心函數庫 ---
def generate_token(system, timestamp, key):
    data_dict = {'system': system, 'time': timestamp, 'key': key}
    data_str = json.dumps(data_dict)
    m = hashlib.md5()
    m.update(data_str.encode('utf-8'))
    return data_str, m.hexdigest().lower()

def get_tw_now():
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    tw_now = utc_now + datetime.timedelta(hours=8)
    return tw_now.strftime("%Y-%m-%d %H:%M:%S")

def get_month_end(dt):
    import calendar
    if pd.isna(dt) or dt is None: return None
    dt = pd.to_datetime(dt)
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return dt.replace(day=last_day)

def get_payment_date(dt):
    if pd.isna(dt) or dt is None: return None
    # 規則：次次月5號撥款
    target_date = (pd.to_datetime(dt).replace(day=1) + pd.DateOffset(months=2))
    return target_date.replace(day=5)

# --- 2. 頁面配置與側邊欄 ---
st.set_page_config(page_title="HURC 數據整合儀表板", layout="wide")

with st.sidebar:
    st.header("🔑 系統參數")
    host = st.text_input("HOST", value="http://john.yilanlun.com:8000")
    system_val = st.text_input("SYSTEM", value="PMISHURC")
    token_key = st.text_input("TOKEN KEY", value="PF$@GESA@F(#!QG_@G@!_^%^C", type="password")
    project_id = st.text_input("PROJECT ID", value="214")
    
    st.divider()
    if 'current_ts' not in st.session_state:
        st.session_state.current_ts = get_tw_now()
    edited_ts = st.text_input("驗證時間戳記", value=st.session_state.current_ts)
    query_date = st.text_input("查詢日期", value=edited_ts.split(" ")[0])

# --- 3. 準備 API 請求 ---
raw_json, final_token = generate_token(system_val, edited_ts, token_key)
ts_encoded = quote(edited_ts, safe="")
base_url = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi"

# --- 4. 主畫面邏輯 ---
st.title("🏗️ HURC 工程資訊與金流預測整合")

if st.button("🚀 執行全面同步分析", use_container_width=True):
    # API 組合
    url_info = f"{base_url}/project_detail/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    url_prog = f"{base_url}/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    
    with st.spinner("正在串接 API 數據..."):
        try:
            requests.packages.urllib3.disable_warnings()
            res_info = requests.get(url_info, timeout=10, verify=False)
            res_prog = requests.get(url_prog, timeout=10, verify=False)
            
            if res_info.status_code == 200:
                data = res_info.json()
                
                # --- 自動抓取基本資料 ---
                # 注意：這裡的 Key 名稱 (contract_amount等) 需與 API 回傳格式一致
                contract_amt = float(data.get('contract_amount', 0))
                duration = int(data.get('duration_days', 0))
                start_d = data.get('start_date', query_date)
                case_name = data.get('project_name', '未命名案件')
                
                # 介面顯示
                st.success(f"✅ 已成功串接案件：{case_name}")
                col1, col2, col3 = st.columns(3)
                col1.metric("契約總價", f"${contract_amt:,.0f}")
                col2.metric("預計工期", f"{duration} 天")
                col3.metric("開工日期", start_d)
                
                # --- 金流編輯區 ---
                st.markdown("---")
                st.subheader("💰 預估金流排程編輯")
                
                if 'design_df' not in st.session_state:
                    st.session_state.design_df = pd.DataFrame([
                        {"期別": "設計一期", "基準點": "合約起始", "相對月數": 3, "比例": 0.10},
                        {"期別": "設計二期", "基準點": "合約起始", "相對月數": 6, "比例": 0.15},
                        {"期別": "設計三期", "基準點": "合約起始", "相對月數": 9, "比例": 0.20},
                        {"期別": "設計四期", "基準點": "預計開工", "相對月數": 6, "比例": 0.45},
                        {"期別": "設計五期", "基準點": "預計完工", "相對月數": 1, "比例": 0.10},
                    ])

                edited_df = st.data_editor(
                    st.session_state.design_df,
                    column_config={
                        "基準點": st.column_config.SelectboxColumn("基準", options=["合約起始", "預計開工", "預計完工"]),
                        "比例": st.column_config.NumberColumn("支付比例", format="%.2f", min_value=0.0, max_value=1.0)
                    },
                    num_rows="dynamic",
                    key="main_editor"
                )

                # --- 這裡可接續你原本的圖表繪製邏輯 ---
                # 使用 contract_amt 進行運算...
                st.info("💡 圖表連動功能已就緒，可依需求加入 S-Curve 或 Bar Chart。")
                
                # 只有進度圖表的部分 (移除預定進度 sch)
                if res_prog.status_code == 200:
                    p_data = res_prog.json().get('mix_data', [])
                    if p_data:
                        st.subheader("📈 實際進度曲線 (不含預定)")
                        df_p = pd.DataFrame(p_data)
                        df_p['date'] = pd.to_datetime(df_p['date'])
                        st.line_chart(df_p.set_index('date')[['act']])

            else:
                st.error(f"API 請求失敗，錯誤碼：{res_info.status_code}")
                
        except Exception as e:
            st.error(f"執行出錯：{str(e)}")

st.divider()
st.caption("系統備註：所有數據均透過安全 Token 驗證並強制使用台灣時區 (+8)。")
