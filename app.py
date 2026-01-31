import streamlit as st
import json
import requests
from openai import OpenAI

# ==========================================
# 1. 基础配置
# ==========================================
st.set_page_config(layout="wide", page_title="AI 配音台 (终极兼容版)")

# 初始化
if 'script_data' not in st.session_state: st.session_state.script_data = None
if 'roles' not in st.session_state: st.session_state.roles = []
if 'role_configs' not in st.session_state: st.session_state.role_configs = {}

# ==========================================
# 2. 核心 API 调用逻辑 (增加 GET/POST 切换)
# ==========================================
def call_indextts_api(full_url, text, config, method="POST"):
    """
    终极版调用函数: 支持 GET 和 POST 两种模式
    """
    if not full_url: return None, "请在侧边栏填写完整API地址"

    # 准备参数
    params = {
        "text": text,
        "text_lang": "zh",
        "speed": 1.0,
        "emotion_mode": config.get("emotion_mode", "same_as_ref")
    }
    
    # 将情感向量转为 JSON 字符串 (如果是 GET 请求，列表/字典必须转字符串)
    if config.get("vectors"):
        params["emotion_vector"] = json.dumps(config.get("vectors"))
    
    # 路径参数
    ref_path = config.get("ref_audio_path")
    if ref_path: params["ref_audio_path"] = ref_path

    # 文件处理
    files = {}
    uploaded_file = config.get("uploaded_file")
    if uploaded_file:
        uploaded_file.seek(0)
        files = {'ref_audio': (uploaded_file.name, uploaded_file, 'audio/wav')}
        # 如果是 GET 模式但上传了文件，这通常是不支持的，只能尝试转为 POST
        if method == "GET": 
            return None, "❌ 错误：上传文件模式必须使用 POST 请求，请在侧边栏切换请求方式。"

    try:
        if method == "POST":
            # POST 模式：如果有文件用 multipart，没文件用 JSON
            if files:
                resp = requests.post(full_url, data=params, files=files, timeout=60)
            else:
                resp = requests.post(full_url, json=params, timeout=60)
        else:
            # GET 模式：所有参数放在 URL 后面 (例如 ?text=hello)
            # GET 不支持上传文件流
            resp = requests.get(full_url, params=params, timeout=60)

        # 结果判读
        if resp.status_code == 200:
            # 检查返回的是不是音频 (防止返回了 WebUI 的 HTML 网页)
            content_type = resp.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                return None, "❌ 错误：返回了网页HTML而不是音频。\n⚠️ 原因：您连接的是 WebUI 界面 (端口7860)，而不是 API 服务 (通常是9880)。"
            return resp.content, None
        elif resp.status_code == 405:
            return None, "❌ 405 Method Not Allowed\n服务端不支持此请求方式。请尝试在侧边栏切换 [请求方式] 为 GET 或 POST。"
        else:
            return None, f"Server Error {resp.status_code}: {resp.text[:200]}"

    except Exception as e:
        return None, f"连接异常: {str(e)}"

# ==========================================
# 3. 简化版 LLM 分析
# ==========================================
def analyze_script(text, key, model):
    client = OpenAI(api_key=key, base_url="https://yunwu.ai/v1")
    try:
        res = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":f"拆分小说为JSON列表:[{{'role':'角色','text':'对白'}}].无Markdown.文本:{text[:2000]}"}]
        )
        return json.loads(res.choices[0].message.content.replace("```json","").replace("```",""))
    except Exception as e: return f"Error: {e}"

# ==========================================
# 4. 侧边栏配置 (UI 升级)
# ==========================================
with st.sidebar:
    st.header("⚙️ 设置面板")
    
    # LLM
    with st.expander("1. 模型设置"):
        key = st.text_input("Yunwu Key", type="password")
        mod = st.text_input("模型ID", "deepseek-chat")

    # TTS (关键修改)
    with st.expander("2. TTS 连接 (关键)", expanded=True):
        st.info("如果 7860 报错，请尝试找一下 9880 端口的地址")
        
        # 让用户自己填完整路径，不要乱猜了
        tts_url = st.text_input(
            "完整 API Url", 
            value="https://ffo5lqa2aqpiq89w-9880.container.x-gpu.com/tts",
            help="尝试把端口从 7860 改成 9880，并在末尾加上 /tts 试试"
        )
        
        # 增加请求方式切换
        req_method = st.radio("请求方式", ["POST", "GET"], horizontal=True, help="如果POST报405，试下GET")

    uploaded = st.file_uploader("导入 TXT", type="txt")

# ==========================================
# 5. 主界面
# ==========================================
st.title("🎧 IndexTTS 配音 (诊断模式)")

# 1. 分析
if uploaded and key:
    if st.button("🚀 第一步：分析剧本"):
        txt = uploaded.getvalue().decode("utf-8")
        res = analyze_script(txt, key, mod)
        if isinstance(res, list):
            st.session_state.script_data = res
            st.session_state.roles = list(set([x['role'] for x in res]))
        else:
            st.error(res)

# 2. 生成
if st.session_state.script_data:
    st.divider()
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("配置")
        for r in st.session_state.roles:
            with st.expander(f"{r}"):
                # 简单起见，只保留文件上传，因为云端通常无法读取路径
                f = st.file_uploader(f"上传 {r} 参考音频", key=f"f_{r}")
                if f:
                    if r not in st.session_state.role_configs: st.session_state.role_configs[r] = {}
                    st.session_state.role_configs[r]['uploaded_file'] = f

    with c2:
        st.subheader("列表")
        for i, line in enumerate(st.session_state.script_data):
            col_text, col_btn = st.columns([4, 1])
            with col_text:
                st.markdown(f"**{line['role']}**: {line['text']}")
            with col_btn:
                if st.button("▶️", key=f"p_{i}"):
                    conf = st.session_state.role_configs.get(line['role'], {})
                    
                    if not conf.get('uploaded_file'):
                        st.warning("请先上传参考音频")
                    else:
                        with st.spinner(f"正在 {req_method} 请求..."):
                            wav, err = call_indextts_api(tts_url, line['text'], conf, req_method)
                            if wav:
                                st.audio(wav, format="audio/wav")
                            else:
                                st.error(err)
            st.divider()
