import streamlit as st
import openai
import json
import requests
import os
import tempfile
import time

# --- 页面全局配置 ---
st.set_page_config(page_title="IndexTTS 高级配音工作台", layout="wide")

# --- CSS 样式优化：让界面更像原生应用 ---
st.markdown("""
<style>
    /* 角色卡片样式 */
    .role-container {
        background-color: #2b2b2b;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #444;
        margin-bottom: 20px;
    }
    .role-header {
        font-size: 20px;
        font-weight: bold;
        color: #fff;
        margin-bottom: 10px;
        border-bottom: 1px solid #555;
        padding-bottom: 5px;
    }
    /* 模拟截图中的深色背景输入框 */
    .stTextInput input {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border: 1px solid #555;
    }
    /* 滑块样式微调 */
    .stSlider > div > div > div > div {
        background-color: #7c4dff;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State 初始化 ---
if 'script_data' not in st.session_state:
    st.session_state.script_data = []
if 'roles' not in st.session_state:
    st.session_state.roles = set()
if 'role_settings' not in st.session_state:
    st.session_state.role_settings = {} # 存储每个角色的详细配置

# ================= 侧边栏配置 =================
st.sidebar.title("🛠️ 系统设置")

with st.sidebar.expander("1. 模型接口 (LLM)", expanded=False):
    llm_base_url = st.text_input("Base URL", value="https://yunwu.ai/v1/")
    llm_api_key = st.text_input("API Key", type="password")
    model_options = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"]
    selected_model = st.selectbox("选择模型", model_options + ["自定义"])
    if selected_model == "自定义":
        selected_model = st.text_input("输入模型名称")

with st.sidebar.expander("2. IndexTTS 接口设置", expanded=True):
    tts_api_url = st.text_input("API 地址", value="http://127.0.0.1:9880/tts_advanced")
    st.caption("注：此接口需支持接收 emotion_vector 和 ref_audio_path 参数")

# ================= 核心函数 =================

def parse_script_with_ai(text):
    """AI 角色识别"""
    if not llm_api_key:
        st.error("请先设置 API Key")
        return None
    
    client = openai.OpenAI(api_key=llm_api_key, base_url=llm_base_url)
    prompt = """
    分析剧本，提取角色和台词。
    格式：JSON 数组 [{"role": "角色名", "text": "台词内容"}]
    如果是旁白，role 填 "旁白"。
    只返回 JSON，无Markdown。
    """
    try:
        with st.spinner("正在分析剧本..."):
            resp = client.chat.completions.create(
                model=selected_model,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
                temperature=0.1
            )
            return json.loads(resp.choices[0].message.content.replace("```json","").replace("```",""))
    except Exception as e:
        st.error(f"解析失败: {e}")
        return None

def generate_audio_advanced(api_url, text, settings, output_path):
    """
    调用支持高级参数的 TTS 接口
    settings: 包含 ref_audio_path, emotion_mode, emotion_vector 等字典
    """
    # 构建符合截图逻辑的 Payload
    payload = {
        "text": text,
        "ref_audio_path": settings.get("ref_audio_path", ""),
        "emotion_control": settings.get("emotion_mode", "使用情感向量"),
        "format": "mp3"
    }
    
    # 只有选择了“使用情感向量”才发送具体的数值
    if settings.get("emotion_mode") == "使用情感向量":
        payload["emotion_vector"] = {
            "happy": settings.get("happy", 0.0),
            "angry": settings.get("angry", 0.0),
            "sad": settings.get("sad", 0.0),
            "fear": settings.get("fear", 0.0),
            "disgust": settings.get("disgust", 0.0),
            "surprise": settings.get("surprise", 0.0),
        }

    try:
        resp = requests.post(api_url, json=payload, timeout=60)
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return True
        else:
            print(f"Error: {resp.text}")
            return False
    except Exception as e:
        print(f"Request Error: {e}")
        return False

# ================= 主界面逻辑 =================

st.title("🎛️ AI 剧本配音 - 高级控制版")

# --- 第一步：上传与识别 ---
uploaded_file = st.file_uploader("1. 上传剧本 (TXT)", type="txt")
if uploaded_file and st.button("开始角色分析"):
    text = uploaded_file.getvalue().decode("utf-8")
    result = parse_script_with_ai(text)
    if result:
        st.session_state.script_data = result
        st.session_state.roles = sorted(list(set(r['role'] for r in result)))
        st.success(f"识别到 {len(st.session_state.roles)} 个角色")

# --- 第二步：高级角色配置（复刻截图界面）---
if st.session_state.roles:
    st.divider()
    st.header("2. 角色音色与情感配置")
    st.info("在此处配置每个角色的参考音频和情感参数，设置将应用于该角色的所有台词。")

    # 为每个角色创建一个配置面板
    for role in st.session_state.roles:
        # 初始化该角色的默认设置
        if role not in st.session_state.role_settings:
            st.session_state.role_settings[role] = {
                "ref_audio_path": "",
                "emotion_mode": "使用情感向量",
                "happy": 0.0, "angry": 0.0, "sad": 0.0, 
                "fear": 0.0, "disgust": 0.0, "surprise": 0.0
            }
        
        settings = st.session_state.role_settings[role]

        with st.expander(f"👤 {role} 配置面板", expanded=False):
            # 布局：左侧参考音频，右侧情感控制
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.markdown("**参考音频 (Reference Audio)**")
                # 选项 1：输入服务器路径 (截图风格)
                path_val = st.text_input(
                    f"本地路径 (如 I:/F5tts/{role}.wav)", 
                    value=settings["ref_audio_path"],
                    key=f"path_{role}"
                )
                
                # 选项 2：上传文件 (适合 Streamlit Cloud)
                uploaded_ref = st.file_uploader(f"或上传音频文件 ({role})", type=["wav", "mp3"], key=f"up_{role}")
                
                # 逻辑：如果有上传，优先使用上传的临时路径，否则使用输入的路径
                if uploaded_ref:
                    # 保存临时文件获取路径
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                        tmp.write(uploaded_ref.getvalue())
                        settings["ref_audio_path"] = tmp.name
                else:
                    settings["ref_audio_path"] = path_val

            with c2:
                st.markdown("**情感控制 (Emotion Control)**")
                mode = st.selectbox(
                    "控制模式", 
                    ["与语音参考相同", "使用情感参考音频", "使用情感向量", "使用文本描述"],
                    index=2, # 默认选中 "使用情感向量"
                    key=f"mode_{role}"
                )
                settings["emotion_mode"] = mode

            # --- 情感向量滑块 (仅当选择“使用情感向量”时显示) ---
            if mode == "使用情感向量":
                st.markdown("---")
                st.markdown("**情感向量调节 (Emotion Vectors)**")
                
                # 使用多列布局复刻截图的排列
                ec1, ec2, ec3 = st.columns(3)
                
                with ec1:
                    settings["happy"] = st.slider("快乐 (Happy)", 0.0, 1.0, settings["happy"], 0.1, key=f"happy_{role}")
                    settings["fear"] = st.slider("恐惧 (Fear)", 0.0, 1.0, settings["fear"], 0.1, key=f"fear_{role}")
                with ec2:
                    settings["angry"] = st.slider("愤怒 (Angry)", 0.0, 1.0, settings["angry"], 0.1, key=f"angry_{role}")
                    settings["disgust"] = st.slider("厌恶 (Disgust)", 0.0, 1.0, settings["disgust"], 0.1, key=f"disgust_{role}")
                with ec3:
                    settings["sad"] = st.slider("悲伤 (Sad)", 0.0, 1.0, settings["sad"], 0.1, key=f"sad_{role}")
                    settings["surprise"] = st.slider("惊讶 (Surprise)", 0.0, 1.0, settings["surprise"], 0.1, key=f"surprise_{role}")

    # --- 第三步：生成 ---
    st.divider()
    if st.button("🚀 开始批量合成", type="primary"):
        st.write("正在根据上述高级配置生成音频...")
        
        progress = st.progress(0)
        results = []
        total = len(st.session_state.script_data)
        temp_dir = tempfile.mkdtemp()

        for i, line in enumerate(st.session_state.script_data):
            role = line['role']
            text = line['text']
            
            # 获取该角色的特定配置
            role_config = st.session_state.role_settings.get(role, {})
            
            file_name = f"{i}_{role}.mp3"
            out_path = os.path.join(temp_dir, file_name)
            
            # 调用接口
            success = generate_audio_advanced(tts_api_url, text, role_config, out_path)
            
            if success:
                results.append({"role": role, "text": text, "file": out_path})
            
            progress.progress((i + 1) / total)
            time.sleep(0.1)

        st.success("合成完毕！")
        for res in results:
            with st.chat_message(name=res['role']):
                st.write(res['text'])
                st.audio(res['file'])
