import streamlit as st
from openai import OpenAI
import json
import requests
import time
import pandas as pd

# --- 页面配置 ---
st.set_page_config(page_title="AI 配音工作台 (生产版)", layout="wide", page_icon="🎙️")

# --- CSS 样式优化 ---
st.markdown("""
<style>
    .role-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #4e8cff; }
    .stButton>button { width: 100%; border-radius: 5px; }
    .success-box { padding: 10px; background-color: #d1e7dd; color: #0f5132; border-radius: 5px; margin-top: 10px; }
    .error-box { padding: 10px; background-color: #f8d7da; color: #842029; border-radius: 5px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 设置与模型")
    
    st.subheader("1. LLM 设置 (Yunwu.ai)")
    yunwu_key = st.text_input("API Key", type="password", help="输入 Yunwu.ai 的 API Key")
    base_url = "https://yunwu.ai/v1/"
    
    # --- 修改点 1：支持自定义模型输入 ---
    st.markdown("**选择或输入模型:**")
    default_models = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet-20240620", "gemini-1.5-pro", "grok-beta", "doubao-pro-32k", "自定义输入 (Custom)"]
    selected_model = st.selectbox("推荐模型列表", default_models, index=0, label_visibility="collapsed")
    
    if selected_model == "自定义输入 (Custom)":
        model_name = st.text_input("请输入模型 ID", value="my-custom-model", help="在此填入平台支持的任意模型ID")
    else:
        model_name = selected_model
    
    st.info(f"当前使用模型: **{model_name}**")
    
    st.divider()
    
    st.subheader("2. IndexTTS2 设置")
    # 默认提示改为内网穿透地址，提醒用户
    tts_api_url = st.text_input("TTS API 地址 (公网URL)", value="http://xxxx.ngrok.app/v1/tts", help="如果是云端运行，请务必填入公网穿透地址，不能填 localhost")
    
    # 增加配音参数微调
    st.caption("全局参数")
    speed_factor = st.slider("语速 (Speed)", 0.5, 2.0, 1.0, 0.1)

# --- 核心功能函数 ---

def analyze_script(text, api_key, model):
    """使用 LLM 分析文本并拆分角色"""
    if not api_key:
        st.error("请先填写 API Key")
        return []
        
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    prompt = f"""
    你是一个配音剧本拆解专家。请将下面的小说/剧本内容拆解为【角色】和【台词】的列表。
    
    规则：
    1. 既然是配音，所有的环境描写、动作描写、心理活动等非对话内容，全部归类为 "旁白"。
    2. 提取对话的说话人名字。
    3. 输出格式必须是纯粹的 JSON 数组，不要包含 ```json 标记。
    格式范例：[{{"role": "旁白", "text": "雨越下越大。"}}, {{"role": "萧炎", "text": "三十年河东，三十年河西！"}}]
    
    待拆解文本如下：
    {text}
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content
        # 强制清理 markdown 格式
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except json.JSONDecodeError:
        st.error("AI 返回的数据格式有误，请重试或更换模型。")
        st.code(content) #由于解析失败，打印原始内容供调试
        return []
    except Exception as e:
        st.error(f"LLM 请求失败: {str(e)}")
        return []

def generate_real_audio(text, role, voice_name, api_url, speed):
    """
    --- 修改点 2：真实的 TTS 请求 ---
    尝试对接 IndexTTS/GPT-SoVITS 类型的接口
    """
    if not api_url:
        return None, "未配置 API URL"
        
    # 这里构建请求体，根据 IndexTTS 的通用协议
    # 注意：不同的搭建包参数名可能不同 (比如 cha_name vs speaker_name)
    # 这里采用目前最通用的参数结构
    payload = {
        "text": text,
        "text_language": "zh",
        "character": voice_name,        # 尝试参数名1
        "speaker_id": voice_name,       # 尝试参数名2 (兼容不同版)
        "role": voice_name,             # 尝试参数名3
        "speed": speed,
        "format": "wav"
    }
    
    headers = {"Content-Type": "application/json"}

    try:
        # 发送真实请求
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        
        # 调试：如果不成功，打印状态码
        if response.status_code != 200:
            err_msg = f"API 报错 {response.status_code}: {response.text[:100]}"
            print(err_msg) # 打印到后台日志
            return None, err_msg
        
        # 检查返回的是否是音频 (Header Check)
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            # 某些 API 返回 JSON 包裹的 base64
            try:
                data = response.json()
                # 如果 API 报错返回了 json 格式的错误信息
                return None, f"API 返回 JSON 而非音频: {data}"
            except:
                pass
        
        # 假定返回的是二进制音频流
        return response.content, "success"
        
    except requests.exceptions.ConnectionError:
        return None, "无法连接 API。请检查地址是否公网可访问（Streamlit Cloud 无法访问 127.0.0.1）。"
    except Exception as e:
        return None, f"请求异常: {str(e)}"

# --- 主界面逻辑 ---

st.title("🎙️ AI 智能配音工作台 (IndexTTS版)")

# 1. 导入与拆解
st.info("💡 提示：本程序在云端运行。请确保您的 TTS 本地服务已开启内网穿透 (Ngrok/Cpolar)，并填入公网地址。")
uploaded_file = st.file_uploader("📂 第一步：上传小说/剧本 (TXT)", type=["txt"])

if 'script_data' not in st.session_state:
    st.session_state['script_data'] = []
if 'roles_list' not in st.session_state:
    st.session_state['roles_list'] = []

if uploaded_file:
    if st.button("🔍 识别角色 & 拆分分镜", type="primary"):
        with st.spinner(f"正在调用 {model_name} 进行智能拆解..."):
            text_str = uploaded_file.read().decode("utf-8")
            # 限制一下文本长度防止 token 溢出，演示用
            if len(text_str) > 3000:
                st.warning("文本过长，仅截取前 3000 字分析。")
                text_str = text_str[:3000]
                
            data = analyze_script(text_str, yunwu_key, model_name)
            if data:
                st.session_state['script_data'] = data
                roles = list(set([d['role'] for d in data]))
                roles.sort()
                # 旁白置顶
                if "旁白" in roles:
                    roles.remove("旁白")
                    roles.insert(0, "旁白")
                st.session_state['roles_list'] = roles
                st.success(f"拆解成功！发现 {len(roles)} 个角色。")

# 2. 角色配音设置
if st.session_state['script_data']:
    st.divider()
    col1, col2 = st.columns([1, 2])
    
    role_map = {}
    
    with col1:
        st.subheader("🎭 角色 <-> 音色映射")
        st.write("请填写 IndexTTS 模型中的**角色名称**或**Speaker ID**")
        container = st.container(height=500)
        with container:
            for role in st.session_state['roles_list']:
                # 默认值逻辑：如果是旁白给个默认，其他空着
                def_val = "旁白_女" if role == "旁白" else ""
                val = st.text_input(f"{role} 的音色ID", value=def_val, key=f"role_{role}", placeholder="例如: 纳西妲_v2")
                role_map[role] = val
    
    with col2:
        st.subheader("📜 分镜预览")
        container_script = st.container(height=500)
        with container_script:
            for item in st.session_state['script_data']:
                r = item['role']
                t = item['text']
                color = "blue" if r=="旁白" else "orange"
                st.markdown(f"**:{color}[{r}]**: {t}")

    # 3. 合成执行
    st.divider()
    st.subheader("🚀 开始配音")
    
    # 检查URL警告
    if "0.0.0.0" in tts_api_url or "127.0.0.1" in tts_api_url or "localhost" in tts_api_url:
        st.warning("⚠️ 检测到您填写的 TTS 地址是本地地址。在 Streamlit Cloud 在线运行时，这会导致连接失败。请使用内网穿透后的 https://xxx.ngrok-free.app 地址。")

    if st.button("⚡ 立即合成所有音频"):
        st.write("---")
        progress_bar = st.progress(0)
        log_area = st.expander("查看详细处理日志", expanded=True)
        
        success_count = 0
        fail_count = 0
        
        for i, item in enumerate(st.session_state['script_data']):
            role_name = item['role']
            text_content = item['text']
            voice_id = role_map.get(role_name, "").strip()
            
            # 如果没填音色，跳过或者用默认
            if not voice_id:
                log_area.write(f"⚠️ 跳过 [{role_name}]：未分配音色ID")
                fail_count += 1
                continue
                
            # 调用真实接口
            audio_bytes, msg = generate_real_audio(text_content, role_name, voice_id, tts_api_url, speed_factor)
            
            if audio_bytes:
                success_count += 1
                # 直接在界面显示播放器
                col_a, col_b = st.columns([1, 6])
                with col_a:
                    st.markdown(f"**{role_name}**")
                with col_b:
                    st.audio(audio_bytes, format='audio/wav')
                    st.caption(f"内容：{text_content}")
            else:
                fail_count += 1
                log_area.error(f"❌ [{role_name}]合成失败: {msg}")
            
            progress_bar.progress((i + 1) / len(st.session_state['script_data']))
            
        if success_count > 0:
            st.success(f"处理完成！成功: {success_count} 条，失败: {fail_count} 条。")
        else:
            st.error("所有条目均合成失败，请检查 API 地址和网络连接。")

