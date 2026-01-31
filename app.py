import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import requests
import os
import time

# --- 页面配置 ---
st.set_page_config(page_title="AI 智能配音工作台", layout="wide", page_icon="🎙️")

# --- CSS 样式优化 (模仿截图风格) ---
st.markdown("""
<style>
    .role-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #4e8cff;
    }
    .dialogue-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 10px;
        margin-bottom: 5px;
        border-radius: 5px;
    }
    .role-label { font-weight: bold; color: #333; }
    .text-content { color: #555; }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 设置与模型")
    
    st.subheader("1. LLM 设置 (Yunwu.ai)")
    yunwu_key = st.text_input("API Key", type="password", help="输入 Yunwu.ai 的 API Key")
    base_url = "https://yunwu.ai/v1/"
    
    # 支持的模型列表，用户也可以手动输入
    default_models = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet-20240620", "gemini-1.5-pro", "grok-beta", "doubao-pro-32k"]
    model_name = st.selectbox("选择或输入 AI 模型 ID", default_models, index=0)
    
    st.divider()
    
    st.subheader("2. IndexTTS2 设置")
    tts_api_url = st.text_input("TTS API 地址", value="http://your-indextts-endpoint/v1/generate", help="填写你的 IndexTTS 云端接口地址")
    
    st.info("提示：请确保你的 IndexTTS 服务已开启并可公网访问。")

# --- 核心功能函数 ---

def analyze_script(text, api_key, model):
    """使用 LLM 分析文本并拆分角色"""
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    prompt = f"""
    你是一个专业的配音剧本拆解专家。
    请分析以下文本，将其拆解为【角色】和【台词】。
    
    要求：
    1. 所有的非对话描写、环境描写归类为角色 "旁白"。
    2. 准确识别说话的角色名字。
    3. 输出必须是严格的 JSON 格式列表，不要包含 Markdown 代码块标记（如 ```json）。
    4. 格式示例：
       [
         {{"role": "旁白", "text": "天空下起了大雨。"}},
         {{"role": "李明", "text": "快跑！别回头！"}}
       ]
    
    待分析文本：
    {text}
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000
        )
        content = response.choices[0].message.content
        # 清理可能存在的 markdown 标记
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        st.error(f"AI 分析失败: {e}")
        return []

def generate_audio_indextts(text, role, voice_id, api_url):
    """
    调用 IndexTTS 进行配音
    注意：这里的 payload 结构取决于你的 IndexTTS 具体实现，通常是参考 GPT-SoVITS 或 Index 类似的接口
    """
    try:
        # 模拟请求结构，请根据实际 IndexTTS API 文档修改 payload
        payload = {
            "text": text,
            "speaker_id": voice_id,  # 或者 character_name
            "language": "zh",
            "format": "wav"
        }
        
        # 示例：如果是 POST 请求
        # response = requests.post(api_url, json=payload, timeout=60)
        
        # --- 模拟代码 (因为没有真实的 IndexTTS 地址) ---
        # 实际使用时请取消注释上面的 request, 并删除下面的模拟 sleep
        time.sleep(1) # 模拟网络延迟
        if not api_url or "your-indextts" in api_url:
             # 如果没有配置真实 API，返回 False 用于演示 UI 报错
             return None 
             
        # 假设返回的是音频二进制数据
        # return response.content
        return b"fake_audio_bytes" 
        
    except Exception as e:
        st.error(f"TTS 合成错误 ({role}): {e}")
        return None

# --- 主界面逻辑 ---

st.title("🎙️ 智能配音分镜系统")

# 1. 步骤一：上传与分析
st.subheader("1. 导入剧本")
uploaded_file = st.file_uploader("选择本地 TXT 文件", type=["txt"])

if 'script_data' not in st.session_state:
    st.session_state['script_data'] = []
if 'roles_list' not in st.session_state:
    st.session_state['roles_list'] = []

if uploaded_file and st.button("开始 AI 角色拆解", type="primary"):
    if not yunwu_key:
        st.warning("请先在左侧输入 API Key")
    else:
        with st.spinner(f"正在使用 {model_name} 分析剧本..."):
            text_content = uploaded_file.read().decode("utf-8")
            script_data = analyze_script(text_content, yunwu_key, model_name)
            
            if script_data:
                st.session_state['script_data'] = script_data
                # 提取所有唯一角色
                unique_roles = list(set([item['role'] for item in script_data]))
                # 确保旁白在第一个
                if "旁白" in unique_roles:
                    unique_roles.remove("旁白")
                    unique_roles.insert(0, "旁白")
                st.session_state['roles_list'] = unique_roles
                st.success(f"拆解完成！共识别出 {len(unique_roles)} 个角色，{len(script_data)} 条分镜。")

# 2. 步骤二：角色配置与预览 (核心 UI)
if st.session_state['script_data']:
    st.divider()
    
    col_left, col_right = st.columns([1, 2])
    
    # --- 左侧：角色配音设置 ---
    with col_left:
        st.subheader("🎭 角色声音配置")
        st.caption("为识别到的每个角色手动分配 IndexTTS 的音色 ID")
        
        role_voice_map = {}
        
        with st.container(height=600): # 滚动区域
            for role in st.session_state['roles_list']:
                st.markdown(f"**{role}**")
                # 这里输入音色 ID，或者你可以改为选择预设好的列表
                voice_id = st.text_input(f"配音 ID/名称", key=f"voice_{role}", placeholder=f"输入 {role} 的音色ID")
                # 也可以加上试听按钮...
                role_voice_map[role] = voice_id
                st.markdown("---")

    # --- 右侧：分镜预览 ---
    with col_right:
        st.subheader("📜 分镜预览")
        
        with st.container(height=600): # 滚动区域
            for idx, item in enumerate(st.session_state['script_data']):
                role = item['role']
                text = item['text']
                
                # 根据角色不同显示不同颜色（简单逻辑）
                bg_color = "#e3f2fd" if role == "旁白" else "#fff3e0"
                border_color = "#2196f3" if role == "旁白" else "#ff9800"
                
                st.markdown(f"""
                <div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; border-left: 4px solid {border_color}; margin-bottom: 8px;">
                    <span style="font-weight:bold; font-size: 0.9em; color: #666;">{role}</span><br>
                    <span style="font-size: 1.1em; color: #333;">{text}</span>
                </div>
                """, unsafe_allow_html=True)

    # 3. 步骤三：合成
    st.divider()
    st.subheader("🚀 生成配音")
    
    if st.button("开始生成所有音频", type="primary"):
        # 检查是否所有角色都配置了声音
        missing_voices = [r for r, v in role_voice_map.items() if not v]
        
        if missing_voices:
            st.warning(f"以下角色尚未配置音色 ID: {', '.join(missing_voices)}。将跳过或使用默认音色。")
        
        if "fake_audio" in str(generate_audio_indextts("", "", "", tts_api_url)):
            st.warning("⚠️ 警告：当前使用的是模拟音频生成逻辑。请在代码 `generate_audio_indextts` 函数中填入真实的 API 请求逻辑。")

        progress_bar = st.progress(0)
        status_text = st.empty()
        
        generated_clips = []
        
        for i, item in enumerate(st.session_state['script_data']):
            role = item['role']
            text = item['text']
            voice_id = role_voice_map.get(role, "default")
            
            status_text.text(f"正在合成 ({i+1}/{len(st.session_state['script_data'])}): [{role}] {text[:15]}...")
            
            # 调用 TTS
            audio_data = generate_audio_indextts(text, role, voice_id, tts_api_url)
            
            if audio_data:
                generated_clips.append({
                    "index": i,
                    "role": role,
                    "audio": audio_data
                })
            
            progress_bar.progress((i + 1) / len(st.session_state['script_data']))
        
        status_text.text("合成完成！")
        
        # 显示结果和下载
        st.success(f"成功生成 {len(generated_clips)} 段音频。")
        
        # 这里演示如何播放第一段，实际项目中通常会合并所有音频
        # 如果需要合并，可以使用 pydub 库处理 audio_data (需要是 wav/mp3 bytes)
        st.write("### 试听片段")
        if generated_clips:
            # 这是一个示例，如果有真实音频数据 unique id
            st.audio(generated_clips[0]['audio'], format="audio/wav")
            st.caption(f"片段 1: {st.session_state['script_data'][0]['text']}")

        # 实际开发建议：主要提供一个ZIP包下载或者合并后的长音频下载

