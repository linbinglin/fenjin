import streamlit as st
from openai import OpenAI
import re

# 设置页面配置
st.set_page_config(
    page_title="AI文案分镜助手",
    page_icon="🎬",
    layout="wide"
)

# --- 侧边栏：配置区域 ---
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    # API Key 输入
    api_key = st.text_input("API Key", type="password", placeholder="sk-xxxxxxxx")
    
    # Base URL 配置
    base_url = st.text_input(
        "Base URL (中转接口地址)", 
        value="https://blog.tuiwen.xyz/v1",
        help="通常填写到 /v1 即可，SDK会自动补全后续路径"
    )
    
    # 模型选择
    model_options = [
        "gpt-4o",
        "deepseek-chat", 
        "claude-3-5-sonnet-20240620",
        "gemini-pro",
        "grok-beta",
        "doubao-pro-32k",
        "gpt-3.5-turbo"
    ]
    
    selected_model = st.selectbox("选择模型 ID", model_options, index=0)
    
    # 允许用户手动输入模型ID
    custom_model = st.checkbox("手动输入模型ID")
    if custom_model:
        model_id = st.text_input("请输入自定义模型ID", value=selected_model)
    else:
        model_id = selected_model

    st.markdown("---")
    st.markdown("💡 **提示**：请确保你的API Key余额充足。
