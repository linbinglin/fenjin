import streamlit as st
import json
import requests
from openai import OpenAI

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(layout="wide", page_title="AI 配音工作台 (智能修复版)")

# 初始化 Session State
if 'script_data' not in st.session_state: st.session_state.script_data = None
if 'roles' not in st.session_state: st.session_state.roles = []
if 'role_configs' not in st.session_state: st.session_state.role_configs = {}
# 新增状态：存储探测到的正确API完整地址
if 'verified_api_url' not in st.session_state: st.session_state.verified_api_url = ""

# ==========================================
# 2. 核心逻辑：智能接口探测
# ==========================================
def probe_api_url(base_url):
    """
    自动探测正确的 API 后缀
    """
    # 去掉末尾斜杠
    base_url = base_url.rstrip("/")
    
    # 常见的 IndexTTS / GPT-SoVITS 接口后缀
    endpoints = [
        "",              # 尝试直接请求 (有些API就是根目录)
        "/tts",          # 最常见的
        "/inference",    # 常见变体
        "/v1/inference", # 规范化接口
        "/api/generate"  # 也是常见的一种
    ]
    
    # 构造一个极简的测试 Payload
    test_payload = {
        "text": "测试",
        "text_lang": "zh", 
        "ref_audio_path": "dummy.wav",
        "prompt_text": "测试",
        "prompt_lang": "zh"
    }

    log_msg = []
    
    for endpoint in endpoints:
        full_url = f"{base_url}{endpoint}"
        try:
            # 尝试发送 POST 请求，超时设置短一点
            resp = requests.post(full_url, json=test_payload, timeout=3)
            
            # 如果状态码是 200 (成功) 或 400/422 (参数错误但路径对了)
            # 说明这个接口是通的，不是 404 也不是 405
            if resp.status_code == 200:
                return True, full_url, f"✅ 成功连接到: {full_url}"
            elif resp.status_code in [400, 422, 500]:
                # 虽然报错但说明服务器接收了请求，只是参数不对，说明路径是对的
                return True, full_url, f"✅ 发现接口(参数待调整): {full_url}"
            else:
                log_msg.append(f"❌ {full_url} 返回 {resp.status_code}")
                
        except Exception as e:
            log_msg.append(f"❌ {full_url} 连接超时或失败")
            
    return False, None, "\n".join(log_msg)

# ==========================================
# 3. 业务逻辑函数
# ==========================================
def analyze_script_llm(text, api_key, model_id):
    client = OpenAI(api_key=api_key, base_url="https://yunwu.ai/v1")
    prompt = f"拆分小说为JSON列表:[{{'role':'角色','text':'对白'}}]. 无Markdown. 文本:{text[:2000]}"
    try:
        resp = client.chat.completions.create(
            model=model_id, messages=[{"role":"user","content":prompt}], temperature=0.1
        )
        return json.loads(resp.choices[0].message.content.replace("```json","").replace("```",""))
    except Exception as e: return f"Error: {e}"

def call_indextts_api(real_url, text, config):
    if not real_url: return None, "请先在侧边栏点击[测试连接]获取正确地址"
    
    # 构建请求
    # 这里处理最棘手的部分：上传文件 vs 路径
    
    # 如果后端是标准的 IndexTTS/GPT-SoVITS 容器，通常接收 JSON
    # 我们需要将 config 里的参数转为后端需要的格式
    
    # 构造 multipart/form-data
    files = {}
    data = {
        "text": text,
        "text_lang": "zh",
        "speed": 1.0,
        "emotion_mode": config.get("emotion_mode", "same_as_ref")
    }
    
    # 处理向量
    if config.get("vectors"):
        data["emotion_vector"] = json.dumps(config.get("vectors"))

    # 处理音频源
    up_file = config.get("uploaded_file")
    ref_path = config.get("ref_audio_path")

    if up_file:
        up_file.seek(0)
        # 关键：字段名通常是 'ref_audio'
        files = {'ref_audio': (up_file.name, up_file, 'audio/wav')}
    elif ref_path:
        data['ref_audio_path'] = ref_path
        
    try:
        # 尝试发送请求
        # 注意：如果files不为空，requests自动设为multipart/form-data，忽略json参数
        # 如果只有data，requests默认用application/x-www-form-urlencoded
        # 所以对于JSON接口，如果没有文件，要用 json=data
        
        if files:
            resp = requests.post(real_url, data=data, files=files, timeout=60)
        else:
            # 如果没有文件上传，优先尝试 JSON 发送 (大多数推理容器首选 JSON)
            resp = requests.post(real_url, json=data, timeout=60)

        if resp.status_code == 200:
            return resp.content, None
        else:
            return None, f"Server Error {resp.status_code}: {resp.text}"
    except Exception as e:
        return None, str(e)

# ==========================================
# 4. 侧边栏
# ==========================================
with st.sidebar:
    st.title("⚙️ 设置面板")
    
    # LLM 设置
    with st.expander("1. 大模型 (分角)", expanded=False):
        key = st.text_input("Yunwu Key", type="password")
        mod = st.selectbox("模型", ["deepseek-chat", "gpt-4o", "自定义"])
        if mod == "自定义": final_mod = st.text_input("ID", "gpt-4-turbo")
        else: final_mod = mod

    # TTS 设置 (关键修改部分)
    with st.expander("2. TTS 服务端 (已修复)", expanded=True):
        raw_url = st.text_input("IndexTTS 根地址", value="https://ffo5lqa2aqpiq89w-7860.container.x-gpu.com/", help="直接复制你图里的那个地址")
        
        col_test, col_status = st.columns([1, 2])
        if col_test.button("🔗 测试连接"):
            with st.spinner("正在探测 API 路径..."):
                success, real_url, msg = probe_api_url(raw_url)
                if success:
                    st.session_state.verified_api_url = real_url
                    st.success("连接成功！")
                    st.toast(msg)
                else:
                    st.error("连接失败")
                    st.text(msg)
        
        if st.session_state.verified_api_url:
            st.caption(f"✅ 实际调用地址: `{st.session_state.verified_api_url}`")
        else:
            st.caption("🔴 未连接")

    st.divider()
    uploaded_txt = st.file_uploader("导入剧本", type="txt")

# ==========================================
# 5. 主界面
# ==========================================
st.title("🎙️ IndexTTS 配音台")

if uploaded_txt and key:
    if st.button("🚀 分析剧本"):
        content = uploaded_txt.getvalue().decode("utf-8")
        res = analyze_script_llm(content, key, final_mod)
        if isinstance(res, list):
            st.session_state.script_data = res
            st.session_state.roles = list(set([x['role'] for x in res]))
else:
    if not uploaded_txt: st.info("请上传剧本文件")

if st.session_state.script_data:
    c1, c2 = st.columns([1.5, 2.5])
    
    # 角色配置区
    with c1:
        st.subheader("角色配置")
        for role in st.session_state.roles:
            if role not in st.session_state.role_configs:
                st.session_state.role_configs[role] = {}
            
            with st.expander(f"👤 {role}", expanded=False):
                type_ = st.radio("源", ["上传文件", "服务器路径"], key=f"t_{role}", horizontal=True)
                
                if type_ == "上传文件":
                    f = st.file_uploader(f"上传 {role} 音频", type=["wav","mp3"], key=f"f_{role}")
                    st.session_state.role_configs[role]['uploaded_file'] = f
                    st.session_state.role_configs[role]['ref_audio_path'] = None
                else:
                    p = st.text_input("路径", value=f"/root/api/wavs/{role}.wav", key=f"p_{role}")
                    st.session_state.role_configs[role]['ref_audio_path'] = p
                    st.session_state.role_configs[role]['uploaded_file'] = None

    # 分镜区
    with c2:
        st.subheader("分镜列表")
        for i, line in enumerate(st.session_state.script_data):
            st.markdown(f"**{line['role']}**: {line['text']}")
            if st.button("▶️ 生成", key=f"b_{i}"):
                url = st.session_state.verified_api_url
                if not url:
                    st.error("请先在侧边栏点击 [测试连接]！")
                else:
                    conf = st.session_state.role_configs.get(line['role'], {})
                    with st.spinner("生成中..."):
                        wav, err = call_indextts_api(url, line['text'], conf)
                        if wav: st.audio(wav, format="audio/wav")
                        else: st.error(err)
            st.divider()
