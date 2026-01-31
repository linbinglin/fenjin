import streamlit as st
import requests
import json
from io import BytesIO

# ==========================================
# 页面配置
# ==========================================
st.set_page_config(layout="wide", page_title="AI 配音助手")

# 初始化
if 'script_data' not in st.session_state:
    st.session_state.script_data = None
if 'verified_api_url' not in st.session_state:
    st.session_state.verified_api_url = None

# ==========================================
# 侧边栏 - 配置
# ==========================================
with st.sidebar:
    st.title("⚙️ 配置中心")

    # API 配置
    with st.expander("TTS 服务端", expanded=True):
        base_url = st.text_input(
            "服务地址", 
            value="https://ffo5lqa2aqpiq89w-7860.container.x-gpu.com/",
            help="填入容器服务的 URL"
        )
        endpoint = st.text_input(
            "手动测试路径 (选填)", 
            value="/tts",
            help="例如 '/tts' 或 '/inference'"
        )
        port_hint = st.info("如果 `7860` 不通，尝试改为 `9880` 或查看服务端配置。")
    
    # 测试连接按钮
    if st.button("🔗 测试连接"):
        st.write("尝试连接服务...")
        full_url = f"{base_url.rstrip('/')}{endpoint}"
        try:
            resp = requests.get(full_url)
            if resp.status_code == 200:
                st.session_state.verified_api_url = full_url
                st.success(f"连接成功: {full_url}")
            else:
                st.error(f"服务端错误 ({resp.status_code}): {resp.text}")
        except Exception as e:
            st.error(f"连接失败: {e}")

# ==========================================
# 主界面
# ==========================================
st.title("🎙️ 配音助手")

if 'verified_api_url' in st.session_state and st.session_state.verified_api_url:
    st.success(f"正在使用服务: {st.session_state.verified_api_url}")
else:
    st.warning("请先在侧边栏测试连接服务！")
