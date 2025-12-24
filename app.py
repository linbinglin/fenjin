import streamlit as st
import requests
import json
import os

# --- 页面配置 ---
st.set_page_config(page_title="精密分镜助理 V1.0", layout="wide")
st.title("🎬 自动文案分镜拆解系统")
st.caption("基于电影解说逻辑：35字/5秒准则 | 场景切换逻辑 | 零文本损耗")

# --- 侧边栏：API 配置 ---
with st.sidebar:
    st.header("⚙️ 模型配置")
    api_url = st.text_input("API 中转地址", value="https://blog.tuiwen.xyz/v1/chat/completions")
    api_key = st.text_input("API Key", type="password")
    
    model_options = [
        "deepseek-chat", 
        "gpt-4o", 
        "claude-3-5-sonnet-20240620", 
        "gemini-1.5-pro", 
        "grok-1",
        "doubao-pro-128k"
    ]
    selected_model = st.text_input("Model ID (手动输入或选择)", value="deepseek-chat")
    
    st.divider()
    st.info("较真提醒：分镜逻辑严格遵循每段不超过35个字符，确保音频对齐。")

# --- 核心提示词（助理角色设定） ---
SYSTEM_PROMPT = """你是一个极其严谨、较真的电影解说分镜专家。
你的任务是将用户提供的【原始文本】重新排列为【分镜脚本】。

执行准则（绝不可违背）：
1. **零损耗原则**：禁止修改、添加或删除原文中的任何一个字。必须保证原文的所有文字按顺序完整出现。
2. **强制分镜逻辑**：
   - 场景转换、角色对话切换、画面动作改变时，必须另起一个分镜序号。
   - **时间对齐约束**：每个分镜的文字长度严格控制在 15-35 个字符之间。如果原句过长，必须在不改变文字的前提下，根据停顿感拆分为多个分镜，以确保单段音频不超过5秒。
3. **消除段落干扰**：忽略输入文本原有的段落格式，将其视为连续流处理，重新根据叙事逻辑和长度限制进行分号。
4. **输出格式**：
   直接输出带序号的分镜列表，格式如下：
   1.分镜内容
   2.分镜内容
   （禁止输出任何开场白、解释或总结语）
"""

def call_ai_api(text):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 清理文本：去掉原有换行，强制AI重新审视结构
    cleaned_text = text.replace("\n", "").replace("\r", "").strip()
    
    payload = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请对以下文本进行分镜处理，记住，不准改动原文任何字句：\n\n{cleaned_text}"}
        ],
        "temperature": 0.3  # 低随机性，保证严谨
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"发生错误：{str(e)}"

# --- 主界面 ---
uploaded_file = st.file_uploader("选择本地 .txt 文案文件", type=['txt'])

if uploaded_file is not None:
    # 读取文件
    original_text = uploaded_file.read().decode("utf-8")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 原始文案")
        st.text_area("内容预览", original_text, height=400)
    
    if st.button("🚀 开始自动化精密分镜"):
        if not api_key:
            st.error("请先在左侧输入 API Key")
        else:
            with st.spinner("助理正在逐字分析剧情，请稍候..."):
                result = call_ai_api(original_text)
                with col2:
                    st.subheader("🎬 分镜结果")
                    st.text_area("分镜脚本", result, height=400)
                    st.download_button("导出分镜脚本", result, file_name="storyboard.txt")

# --- 底部工作日志 ---
st.divider()
st.caption("较真助理日志：待命。已准备好处理任何长度的文本流。")
