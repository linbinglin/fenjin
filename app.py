import streamlit as st
import openai
import json
import requests
import os
import tempfile
import time

# --- 页面配置 ---
st.set_page_config(page_title="AI 智能分角 + IndexTTS 配音", layout="wide")

# --- 自定义 CSS 样式 ---
st.markdown("""
<style>
    .role-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border-left: 5px solid #4CAF50;
    }
    .text-content {
        color: #333;
        font-size: 16px;
    }
    .stTextInput > label {
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- 会话状态初始化 ---
if 'script_data' not in st.session_state:
    st.session_state.script_data = [] # 存储分角后的剧本
if 'roles' not in st.session_state:
    st.session_state.roles = set()    # 存储所有角色
if 'role_map' not in st.session_state:
    st.session_state.role_map = {}    # 存储 剧本角色 -> IndexTTS角色名 的映射

# --- 侧边栏：设置 ---
st.sidebar.title("🛠️ 设置面板")

# 1. 大模型设置
with st.sidebar.expander("1. 角色识别模型设置 (Yunwu/OpenAI)", expanded=True):
    base_url = st.text_input("LLM Base URL", value="https://yunwu.ai/v1/")
    llm_api_key = st.text_input("LLM API Key", type="password", help="请输入你的 Yunwu 或 OpenAI API Key")
    
    model_options = [
        "deepseek-chat",
        "gpt-4o",
        "claude-3-5-sonnet-20240620",
        "gemini-1.5-pro",
        "grok-beta",
        "doubao-pro-4k"
    ]
    selected_model = st.selectbox("选择 AI 模型", model_options + ["自定义..."])
    if selected_model == "自定义...":
        selected_model = st.text_input("输入自定义模型名称")

# 2. 配音接口设置
with st.sidebar.expander("2. IndexTTS 配音接口设置", expanded=True):
    st.info("请确保你的 IndexTTS 服务已启动并可被公网访问（如果是 Streamlit Cloud）")
    # 这里填写你的 API 地址，比如 http://123.45.67.89:5000/tts 或 https://api.yourdomain.com/v1/generate
    tts_api_url = st.text_input("IndexTTS API 地址", value="http://127.0.0.1:9880/tts")
    
    st.markdown("**API 调用参数说明:**")
    st.caption("本程序将默认以 POST 方式发送 JSON 数据：`{'text': '...', 'speaker': '...'}`。如需更改字段名请修改代码中 `generate_audio_index` 函数。")

# --- 核心功能函数 ---

def parse_script_with_ai(text, api_key, base_url, model):
    """调用大模型进行分角识别"""
    if not api_key:
        st.error("请先填写 LLM API Key")
        return None
        
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    
    system_prompt = """
    你是一个专业的剧本分角助手。请阅读用户提供的文本，识别每一句话的说话人。
    如果文本是环境描写、动作描写或内心独白，且没有明确说话人，请归类为 "旁白"。
    
    请严格按照以下 JSON 格式返回结果（不要包含 Markdown 代码块标记）：
    [
        {"role": "旁白", "text": "在合欢宗每双修一次..."},
        {"role": "火冥", "text": "你要挖鳞片就快一点挖..."},
        {"role": "旁白", "text": "紧接着又一道清冷的声音响起"},
        {"role": "凌绝", "text": "苏月我虽然需要火蛟鳞片..."}
    ]
    只返回 JSON 数据，不要返回其他任何解释。
    """
    
    try:
        with st.spinner(f"正在使用 {model} 分析剧本角色..."):
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1
            )
            content = response.choices[0].message.content
            # 清理可能存在的 markdown 标记
            content = content.replace("```json", "").replace("```", "").strip()
            data = json.loads(content)
            return data
    except Exception as e:
        st.error(f"AI 识别失败: {str(e)}")
        return None

def generate_audio_index(api_url, text, speaker_name, output_file):
    """
    调用 IndexTTS 接口生成音频
    注意：不同的 IndexTTS 版本参数可能不同（如 spk_id, character, speaker 等）
    请根据你的实际 API 文档修改下面的 json payload 字段。
    """
    headers = {'Content-Type': 'application/json'}
    
    # --- 关键：根据你的 API 格式修改这里 ---
    payload = {
        "text": text,           # 文本内容
        "speaker": speaker_name, # 角色名称/ID
        "format": "mp3",        # 格式
        "speed": 1.0            # 语速
    }
    # ------------------------------------

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=60)
        
        if response.status_code == 200:
            # 假设返回的是二进制音频文件
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return True
        else:
            st.error(f"API 错误 [{response.status_code}]: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        st.error(f"无法连接到 API 地址: {api_url}。如果是在线运行，请确保地址是公网可访问的。")
        return False
    except Exception as e:
        st.error(f"请求发生错误: {str(e)}")
        return False

# --- 主界面 ---

st.title("🎙️ AI 分角 + IndexTTS 配音助手")

# 1. 文件上传
uploaded_file = st.file_uploader("📂 第一步：上传 TXT 剧本文件", type=["txt"])

if uploaded_file is not None:
    stringio = uploaded_file.getvalue().decode("utf-8")
    
    with st.expander("查看原始文本"):
        st.text_area("原始内容", stringio, height=150)
    
    # 2. AI 分角按钮
    if st.button("🤖 1. 开始 AI 角色识别"):
        result = parse_script_with_ai(stringio, llm_api_key, base_url, selected_model)
        if result:
            st.session_state.script_data = result
            # 提取所有角色
            roles = set(item['role'] for item in result)
            st.session_state.roles = roles
            st.success(f"识别成功！共发现 {len(roles)} 个角色。")

# 3. 角色映射与配音
if st.session_state.script_data:
    st.divider()
    st.header("🎭 第二步：角色音色映射")
    st.info("请为左侧识别出的剧本角色，填写右侧 IndexTTS 模型中对应的角色名或 ID。")
    
    cols = st.columns(3)
    role_list = list(st.session_state.roles)
    
    # 动态生成输入框，让用户输入 API 需要的 speaker 名称
    for i, role in enumerate(role_list):
        with cols[i % 3]:
            # 默认填入角色名本身，方便用户修改
            val = st.text_input(f"剧本角色: 【{role}】", value=role, key=f"map_{role}")
            st.session_state.role_map[role] = val
            st.caption(f"将在 API 中调用: {val}")

    st.divider()
    st.header("🎬 第三步：生成配音")
    
    # 预览
    with st.expander("分镜预览 (点击展开)"):
        for item in st.session_state.script_data:
            st.markdown(f"**{item['role']}**: {item['text']}")
    
    if st.button("🎧 调用 IndexTTS 开始合成", type="primary"):
        if not tts_api_url:
            st.error("请在侧边栏填写 IndexTTS API 地址！")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            audio_results = []
            temp_dir = tempfile.mkdtemp()
            
            total_lines = len(st.session_state.script_data)
            
            for i, item in enumerate(st.session_state.script_data):
                role = item['role']
                text = item['text']
                # 获取映射后的 API 角色名
                api_speaker = st.session_state.role_map.get(role, role)
                
                status_text.text(f"正在生成 ({i+1}/{total_lines}): {role} -> API[{api_speaker}]")
                
                filename = f"{i:03d}_{role}.mp3"
                filepath = os.path.join(temp_dir, filename)
                
                # 调用同步 HTTP 接口
                success = generate_audio_index(tts_api_url, text, api_speaker, filepath)
                
                if success:
                    audio_results.append({
                        "role": role,
                        "text": text,
                        "file": filepath
                    })
                else:
                    status_text.warning(f"第 {i+1} 句生成失败，跳过。")
                
                progress_bar.progress((i + 1) / total_lines)
                time.sleep(0.1) # 防止请求过快
                
            status_text.success("✅ 生成流程结束！")
            
            # 播放结果
            st.subheader("播放列表")
            for audio in audio_results:
                st.markdown(f"**{audio['role']}**: {audio['text']}")
                st.audio(audio['file'])
