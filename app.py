import streamlit as st
import json
import requests
from openai import OpenAI
import io

# ==========================================
# 1. 页面初始化
# ==========================================
st.set_page_config(layout="wide", page_title="AI 配音工作台 (修复版)")

# 初始化 Session State
if 'script_data' not in st.session_state:
    st.session_state.script_data = None
if 'roles' not in st.session_state:
    st.session_state.roles = []
if 'role_configs' not in st.session_state:
    st.session_state.role_configs = {}

# ==========================================
# 2. 核心逻辑函数
# ==========================================

def analyze_script_llm(text, api_key, model_id):
    """Yunwu AI 角色拆分"""
    client = OpenAI(api_key=api_key, base_url="https://yunwu.ai/v1")
    
    prompt = f"""
    将文本拆分为JSON列表：[{{"role": "角色名", "text": "对白"}}]。
    不要Markdown。
    文本：{text[:3000]}
    """
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        content = response.choices[0].message.content.replace("```json", "").replace("```", "")
        return json.loads(content)
    except Exception as e:
        return f"Error: {e}"

def call_indextts_api(api_url, text, config):
    """
    IndexTTS 配音调用 (支持文件上传 & 路径)
    """
    # 1. 简单的地址修正 (解决 Method Not Allowed)
    # 如果用户填写的地址是以 .app 结尾并没有带 /tts，我们尝试智能补全
    # 注意：这取决于您的IndexTTS具体部署代码，常见的endpoint是 /tts 或 /
    # 您可以在侧边栏手动修改完整的 API URL
    
    if not api_url: return None, "未填写API地址"

    # 准备基础参数
    # 如果是上传文件，必须使用 multipart/form-data 格式发送
    # requests 库中，files 参数会自动将 header 转为 multipart
    
    try:
        data_params = {
            "text": text,
            "text_lang": "zh",
            "emotion_mode": config.get("emotion_mode", "same_as_ref"),
            "speed": 1.0
        }

        # 处理情感向量
        vectors = config.get("vectors", {})
        if vectors:
            # 很多API要求向量转为JSON字符串传递
            data_params["emotion_vector"] = json.dumps(vectors)

        uploaded_file = config.get("uploaded_file") # 用户上传的文件对象
        path_str = config.get("ref_audio_path")     # 用户填写的路径字符串
        
        files = {}
        
        # 优先使用上传的文件
        if uploaded_file:
            # 重置指针
            uploaded_file.seek(0)
            # 发送文件二进制流，字段名通常是 'ref_audio' 或 'refer_wav_path'
            # 您需要根据您的后端API文档确认这个 key 的名字，这里假设是 'ref_audio'
            files = {
                'ref_audio': (uploaded_file.name, uploaded_file, 'audio/wav')
            }
        elif path_str:
            # 如果没上传文件，但有路径，则作为普通表单字段发送
            data_params["ref_audio_path"] = path_str

        # 发送请求
        # 注意：使用 files 时，data_params 会作为 form-data 发送，而不是 json
        response = requests.post(api_url, data=data_params, files=files if files else None, timeout=60)
        
        if response.status_code == 200:
            return response.content, None
        elif response.status_code == 405:
            return None, f"❌ 405错误：请求方法不被允许。\n请检查API地址后缀！\n通常API地址不是根目录，而是类似: \n{api_url}/tts \n或 {api_url}/inference"
        else:
            return None, f"服务端报错: {response.status_code} - {response.text}"
            
    except Exception as e:
        return None, f"请求异常: {str(e)}"

# ==========================================
# 3. 侧边栏配置
# ==========================================
with st.sidebar:
    st.header("⚙️ 设置")
    
    # 1. LLM 设置
    with st.expander("🤖 模型设置", expanded=False):
        user_api_key = st.text_input("Yunwu API Key", type="password")
        model_options = ["deepseek-chat", "gpt-4o", "gemini-3-pro-preview", "🔃 自定义输入"]
        opt = st.selectbox("选择模型", model_options)
        if opt == "🔃 自定义输入":
            final_model = st.text_input("输入模型ID", "gpt-4-turbo")
        else:
            final_model = opt

    # 2. TTS 后端设置 (解决 405 问题)
    with st.expander("🔊 TTS 服务端", expanded=True):
        st.info("⚠️ 注意：API地址通常以 /tts 或 /generate 结尾")
        tts_api_input = st.text_input(
            "API 完整地址", 
            # 帮用户预设一个常见的后缀，避免直接填根域名
            value="http://127.0.0.1:9880/tts", 
            help="如果是Ngrok，请确保填写的不是WebUI地址，而是API Endpoint"
        )

    st.divider()
    uploaded_file = st.file_uploader("📂 导入剧本 TXT", type="txt")

# ==========================================
# 4. 主流程
# ==========================================
st.title("🎙️ 智能配音工作台 (Fix)")

# [步骤 1: 拆分文本]
if uploaded_file and user_api_key:
    if st.button("🚀 分析剧本"):
        txt = uploaded_file.getvalue().decode("utf-8")
        with st.spinner("AI 正在拆分角色..."):
            res = analyze_script_llm(txt, user_api_key, final_model)
            if isinstance(res, list):
                st.session_state.script_data = res
                st.session_state.roles = list(set([x['role'] for x in res]))
                st.success("✅ 拆分完成")
            else:
                st.error(f"分析失败: {res}")

# [步骤 2: 配音面板]
if st.session_state.script_data:
    c1, c2 = st.columns([1.5, 2.5])
    
    # --- 左侧：角色配置 (增加上传功能) ---
    with c1:
        st.subheader("🎚️ 角色音色设置")
        for role in st.session_state.roles:
            if role not in st.session_state.role_configs:
                st.session_state.role_configs[role] = {}
                
            with st.expander(f"👤 {role}", expanded=False):
                # 选项：使用文件上传 还是 服务器路径
                source_type = st.radio("音色来源", ["🔼 上传本地音频", "🔗 服务器文件路径"], key=f"src_{role}", horizontal=True)
                
                if source_type == "🔼 上传本地音频":
                    # [修复问题1] 添加上传控件
                    up_file = st.file_uploader(f"上传 {role} 的参考音频", type=["wav", "mp3"], key=f"up_{role}")
                    st.session_state.role_configs[role]['uploaded_file'] = up_file
                    st.session_state.role_configs[role]['ref_audio_path'] = None # 清空路径
                else:
                    user_path = st.text_input(f"服务器路径", value=f"D:/Data/{role}.wav", key=f"path_{role}")
                    st.session_state.role_configs[role]['ref_audio_path'] = user_path
                    st.session_state.role_configs[role]['uploaded_file'] = None # 清空文件

                # 情感
                emo = st.selectbox("情感模式", ["与参考音频相同", "使用情感向量"], key=f"emm_{role}")
                st.session_state.role_configs[role]['emotion_mode'] = emo
                
                if emo == "使用情感向量":
                    v = {}
                    cc1, cc2 = st.columns(2)
                    v['happy'] = cc1.slider("Joy", 0.0, 1.0, key=f"h_{role}")
                    v['sad'] = cc2.slider("Sad", 0.0, 1.0, key=f"s_{role}")
                    st.session_state.role_configs[role]['vectors'] = v

    # --- 右侧：合成 ---
    with c2:
        st.subheader("📜 合成列表")
        for i, line in enumerate(st.session_state.script_data):
            role = line['role']
            text = line['text']
            
            with st.container():
                st.markdown(f"**{role}**: {text}")
                if st.button("▶️ 生成音频", key=f"btn_{i}"):
                    conf = st.session_state.role_configs.get(role, {})
                    
                    # 检查是否配置了声音
                    if not conf.get('uploaded_file') and not conf.get('ref_audio_path'):
                        st.warning("⚠️ 请先在左侧上传音频或填写路径！")
                    else:
                        with st.spinner("请求中..."):
                            wav, err = call_indextts_api(tts_api_input, text, conf)
                            if wav:
                                st.audio(wav, format="audio/wav")
                            else:
                                st.error(err)
            st.divider()
