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

# 頁面配置
st.set_page_config(page_title="HURC 數據監測整合版", layout="wide")

# --- 1. 核心函數 ---
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

# --- 2. 初始化 Session State ---
if 'file_data' not in st.session_state:
    st.session_state.file_data = None
if 'type_data' not in st.session_state:
    st.session_state.type_data = None
if 'prog_data' not in st.session_state:
    st.session_state.prog_data = None

# --- 3. 側邊欄設定 ---
with st.sidebar:
    st.header("🔑 系統參數")
    host = st.text_input("HOST", value="http://john.yilanlun.com:8000")
    system_val = st.text_input("SYSTEM", value="PMISHURC")
    token_key = st.text_input("TOKEN KEY", value="PF$@GESA@F(#!QG_@G@!_^%^C", type="password")
    
    st.divider()
    st.subheader("🏢 專案選擇")
    
    # 完整的 ID 對照表
    PROJECT_MAP = {
        "上林好室": "110", "大華安居A": "135", "大華安居B": "162", "山明安居": "111",
        "中美安居": "144", "中美好室": "85", "中雅安居": "82", "五谷好室A": "33",
        "五谷好室B": "192", "仁和好室": "138", "仁武安居": "67", "仁義好室": "167",
        "公誠安居": "61", "六安好室": "203", "友忠好室": "63", "太武安居": "113",
        "文仁安居": "91", "文學好室": "107", "斗六好室": "56", "水秀安居": "112",
        "北昌安居": "201", "平實安居A": "194", "平實安居B": "197", "平實安居C": "198",
        "平實安居D": "178", "本和安居": "101", "正強安居": "118", "永城好室": "190",
        "永清安居A": "117", "永清安居B": "163", "永清安居C": "179", "永富好室": "180",
        "永福好室": "121", "白鷺安居": "207", "石平好室A": "159", "石平好室B": "160",
        "光明安居": "89", "光春好室": "108", "光環安居": "55", "吉峰安居": "114",
        "安寮好室": "139", "朴子安居": "173", "江翠好室": "37", "竹山好室": "153",
        "沙崙安居": "181", "和順安居": "115", "坤門安居": "201", "延吉好室": "35",
        "明仁好室": "52", "明新安居": "196", "明陀好室": "78", "東仁安居": "80",
        "東光好室": "125", "東橋安居": "83", "松竹好室": "126", "武東好室": "182",
        "玫瑰好室": "38", "芝山安居": "151", "金湖安居": "133", "長勝好室": "124",
        "建功安居": "129", "恆春好室": "209", "春社安居A": "88", "美崙安居": "102",
        "美都安居": "46", "倉前安居": "95", "凌霄好室": "131", "埔心安居A": "119",
        "埔心安居B": "204", "埔心安居C": "205", "淡金安居": "127", "淡海安居": "79",
        "深坑安居": "193", "清豐安居": "66", "莒光安居": "54", "連城安居": "92",
        "頂埔安居": "122", "頂福安居-A基地": "60", "頂福安居-B基地": "75",
        "勝利安居A": "140", "勝利安居B": "199", "勝利安居C": "184", "勝利安居D": "200",
        "博愛安居": "64", "富台安居": "145", "富貴好室": "32", "惠民安居": "84",
        "湧光安居": "128", "貴和安居A": "47", "貴和安居A-慈光廿六村職務宿舍": "69",
        "貴和安居B": "169", "開南安居": "50", "慈文安居": "49", "新市安居": "65",
        "新平安居": "161", "新盛好室": "152", "新都安居A": "30", "新都安居B": "185",
        "新湖好室": "100", "溪洲好室": "212", "瑞屏安居": "72", "稚匯好室": "28",
        "萬華安居AB": "39", "裕忠安居": "149", "過嶺安居": "171", "廍子安居": "116",
        "榮泉安居": "90", "漳和安居": "189", "福山安居": "68", "福安安居A": "195",
        "福城好室": "134", "福清安居": "188", "福樂安居": "62", "鳳翔安居": "51",
        "鳳誠&鳳松安居": "45", "億載安居": "109", "德光安居": "214", "德美好室": "136",
        "德穗安居-社會住宅": "132", "德穗安居-": "215", "樂善安居": "120", "稻香安居": "212",
        "黎孝好室A": "216", "黎孝好室B": "217", "學士安居": "58", "樹德安居A": "99",
        "樹德安居B": "158", "橋北安居": "86", "橋新安居A": "186", "橋新安居B": "187",
        "橋新安居C": "210", "興邦安居A": "96", "興邦安居B": "123", "靜修好室A": "154",
        "靜修好室B": "155", "頭家安居": "57", "龍安安居": "81", "龍岡好室-社會住宅": "48",
        "龍岡好室-龍翔新城職務宿舍": "70", "懷石好室": "29", "鯤鯓安居": "148", "寶桑好室": "94",
        "鶯陶安居": "53", "鶴聲好室": "191", "新民好室": "202", "啟賢安居": "206",
        "溪湖好室": "211", "大平安居": "213", "豐興安居": "218", "七賢安居": "219"
    }
    
    # 使用 selectbox 讓使用者選擇名稱
    selected_name = st.selectbox(
        "請選擇專案名稱",
        options=sorted(list(PROJECT_MAP.keys())), # 排序讓搜尋更方便
        index=0
    )
    
    # 根據選取的名稱獲得 ID
    project_id = PROJECT_MAP[selected_name]
    st.info(f"📍 已選擇 ID: `{project_id}`")
    
    st.divider()
    st.subheader("🇹🇼 台灣時間控制")
    if 'current_ts' not in st.session_state:
        st.session_state.current_ts = get_tw_now()

    edited_ts = st.text_input("驗證時間戳記", value=st.session_state.current_ts)
    query_date = st.text_input("查詢日期", value=edited_ts.split(" ")[0])

    if st.button("🕒 同步目前時間"):
        st.session_state.current_ts = get_tw_now()
        st.rerun()

# --- 4. 主畫面邏輯 ---
st.title("🏗️ HURC 工程數據監測儀表板")

raw_json, final_token = generate_token(system_val, edited_ts, token_key)
ts_encoded = quote(edited_ts, safe="")

# 同步按鈕：僅負責「抓取數據並存入 Session」
if st.button("🚀 執行全面同步", use_container_width=True):
    url_prog = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_progress/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    url_type = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/dailyreport_type_progress/?project_id={project_id}&date={query_date}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    url_file = f"{host.rstrip('/')}/rcm/api/v1/projectinfoapi/storage_file_list/?project_id={project_id}&system={system_val}&timestamp={ts_encoded}&token={final_token}"
    
    with st.spinner("正在抓取數據..."):
        try:
            requests.packages.urllib3.disable_warnings()
            resp_file = requests.get(url_file, timeout=10, verify=False)
            resp_type = requests.get(url_type, timeout=10, verify=False)
            resp_prog = requests.get(url_prog, timeout=10, verify=False)
            
            if resp_file.status_code == 200: st.session_state.file_data = resp_file.json()
            if resp_type.status_code == 200: st.session_state.type_data = resp_type.json()
            if resp_prog.status_code == 200: st.session_state.prog_data = resp_prog.json()
            
            st.success("數據同步完成！")
        except Exception as e:
            st.error(f"連線異常：{str(e)}")

# --- 5. 數據顯示區 (重要：縮排已退回，與 if st.button 平行) ---
if st.session_state.file_data is not None:
    tab1, tab2, tab3, tab4 = st.tabs(["📂 檔案系統列表", "📋 分項進度", "📈 總進度曲線", "🛠️ 系統診斷"])
    
    with tab1:
        df_raw = pd.DataFrame(st.session_state.file_data)
        
        # 欄位改名邏輯
        rename_dict = {}
        for col in df_raw.columns:
            if col.lower() == 'name': rename_dict[col] = "名稱"
            if col.lower() == 'tags': rename_dict[col] = "標籤"
        
        df_display = df_raw.rename(columns=rename_dict)
        display_cols = [c for c in ["名稱", "標籤"] if c in df_display.columns]
        if display_cols:
            df_display = df_display[display_cols]

        if not df_display.empty:
            search_query = st.text_input("🔍 搜尋檔案關鍵字", placeholder="輸入名稱或標籤...", key="file_search_input")
            
            if search_query:
                mask = df_display.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
                df_filtered = df_display[mask]
                st.dataframe(df_filtered, use_container_width=True)
            else:
                st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("查無檔案數據。")

    with tab2:
        if st.session_state.type_data:
            df_type = pd.DataFrame(st.session_state.type_data)
            if not df_type.empty:
                st.dataframe(df_type, use_container_width=True)
                if 'delayed' in df_type.columns and 'name' in df_type.columns:
                    st.bar_chart(df_type.set_index('name')['delayed'])
            else:
                st.warning("該日期無分項進度。")

    with tab3:
        if st.session_state.prog_data:
            p_data = st.session_state.prog_data.get('mix_data', [])
            if p_data:
                df_p = pd.DataFrame(p_data)
                df_p['date'] = pd.to_datetime(df_p['date'])
                st.line_chart(df_p.set_index('date')[['act']])
            else:
                st.warning("無進度數據。")

    with tab4:
        st.write("**加密基準 JSON:**")
        st.code(raw_json)
        st.write("**目前 Token:**", final_token)
else:
    st.info("💡 請點擊上方「執行全面同步」按鈕以開始載入數據。")

st.divider()
st.caption("時區校正：UTC+8 (Taipei) | 搜尋連動：已啟用 Session 緩存機制")

