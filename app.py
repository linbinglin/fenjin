import streamlit as st
from openai import OpenAI
import json
import requests
import time
import base64

# --- 页面配置 ---
st.set_page_config(page_title="AI 声音克隆工作台 (F5-TTS/IndexTTS版)", layout="wide", page_icon="🎙️")

# --- CSS 样式优化 ---
st.markdown("""
<style>
    .role-expander { border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 10px; }
    .stSlider > div { padding-top: 0px; padding-bottom: 10px; }
    .emotion-label { font-size: 0.8rem; color: #666; }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 全局设置")
    
    st.subheader("1. LLM 设置 (Yunwu.ai)")
    yunwu_key = st.text_input("API Key", type="password")
    base_url = "https://yunwu.ai/v1/"
    
    # 模型选择
    st.markdown("**选择核心模型:**")
    default_models = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet-20240620", "自定义输入"]
    selected_model = st.selectbox("模型列表", default_models, label_visibility="collapsed")
    if selected_model == "自定义输入":
        model_name = st.text_input("输入模型 ID", value="my-model")
    else:
        model_name = selected_model
    
    st.divider()
    
    st.subheader("2. 克隆接口设置")
    tts_api_url = st.text_input("API 地址 (URL)", value="http://xxxx.ngrok.app/v1/tts_clone", help="指向支持克隆参数的 API 接口")
    global_speed = st.slider("全局语速", 0.5, 2.0, 1.0)
    
    st.info("提示：请确保后端 API 支持 `ref_audio_path` 或 `emotion` 参数（如 F5-TTS, GPT-SoVITS 增强版）。")

# --- 核心功能函数 ---

def analyze_script(text, api_key, model):
    """拆解剧本 (保持不变)"""
    client = OpenAI(api_key=api_key, base_url=base_url)
    prompt = f"""
    将以下小说/剧本拆解为【角色】和【台词】。
    所有非对话描写归为 "旁白"。
    输出纯 JSON 列表，无 Markdown。
    格式：[{{"role": "旁白", "text": "..."}}, {{"role": "李四", "text": "..."}}]
    文本：{text[:3000]}
    """
    try:
        response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0.1)
        content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except:
        return []

def generate_cloned_audio(text, config, api_url, speed):
    """
    高级克隆合成函数
    config: 包含参考音频路径、情感向量的字典
    """
    if not api_url: return None, "无 API 地址"
    
    # --- 构建高级 Payload (根据 F5-TTS / SoVITS 常见结构) ---
    # 注意：你需要根据你自己后端的实际 API 文档调整 key 的名字
    payload = {
        "text": text,
        "text_language": "zh",
        "speed": speed,
        
        # 1. 声音克隆参数
        # 优先使用用户填写的服务器路径，其次尝试处理上传的文件(这里简化为路径逻辑)
        "ref_audio_path": config.get('ref_audio_path', ""), 
        "prompt_text": "", # 如果需要参考音频对应的字幕，可以在 UI 增加输入框
        
        # 2. 情感控制参数
        "emotion_mode": config.get('emotion_mode', "same_as_ref"),
        
        # 将滑块的值组合成向量数组 [happy, angry, sad, fear, disgust, surprise]
        "emotion_vector": [
            config.get('happy', 0),
            config.get('angry', 0),
            config.get('sad', 0),
            config.get('fear', 0),
            config.get('disgust', 0),
            config.get('surprise', 0)
        ],
        "format": "wav"
    }

    try:
        # 如果是上传方式，通常需要用 multipart/form-data，这里为了通用展示 post json
        # 实际对接时，如果此时 config['ref_file_bytes'] 存在，你可能需要转换成 base64 放到 payload 里
        if config.get('ref_file_base64'):
             payload['ref_audio_base64'] = config['ref_file_base64']

        resp = requests.post(api_url, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.content, "success"
        else:
            return None, f"API 错误 {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return None, str(e)

# --- 主界面 ---

st.title("🎙️ AI 声音克隆与情感控制")

# 1. 剧本加载
uploaded_file = st.file_uploader("📂 上传 TXT 剧本", type=["txt"])
if uploaded_file and st.button("开始拆解角色"):
    st.session_state['script_data'] = analyze_script(uploaded_file.read().decode("utf-8"), yunwu_key, model_name)
    roles = list(set([d['role'] for d in st.session_state['script_data']]))
    if "旁白" in roles: roles.insert(0, roles.pop(roles.index("旁白")))
    st.session_state['roles_list'] = roles
    st.rerun()

# 2. 核心：高级配音设置面板 (模仿截图)
if 'roles_list' in st.session_state and st.session_state['roles_list']:
    st.divider()
    col_conf, col_preview = st.columns([5, 4])
    
    # 存储所有角色的配置
    role_configs = {}
    
    with col_conf:
        st.subheader("🎛️ 角色音色克隆面板")
        st.caption("为每个角色配置独立的参考音频和情感参数")
        
        # 遍历所有角色生成控制面板
        for role in st.session_state['roles_list']:
            # 使用 expander 模仿截图中的卡片效果
            with st.expander(f"👤 角色配置：{role}", expanded=False):
                c1, c2 = st.columns([1, 1])
                
                # --- 部分 1: 参考音频 (Clone) ---
                with c1:
                    st.markdown("##### 1. 参考音频 (Reference)")
                    tab1, tab2 = st.tabs(["服务端路径", "上传文件"])
                    with tab1:
                        # 模仿截图中直接填写硬盘路径 I:/F5tts/...
                        ref_path = st.text_input("音频路径", key=f"path_{role}", placeholder="例如: /data/wavs/xiao_yan.wav")
                    with tab2:
                        ref_upload = st.file_uploader("选择音频", key=f"up_{role}", type=['wav','mp3'])
                
                # --- 部分 2: 情感控制 (Emotion) ---
                with c2:
                    st.markdown("##### 2. 情感控制 (Emotion)")
                    # 情感模式下拉框
                    emo_mode = st.selectbox(
                        "情感模式", 
                        ["与语音参考相同 (Default)", "使用情感向量 (Vector)", "文本描述 (Text)"], 
                        key=f"emo_mood_{role}"
                    )
                    
                    # 情感向量滑块 (只有选中 Vector 时显示)
                    emo_data = {}
                    if emo_mode == "使用情感向量 (Vector)":
                        st.markdown("**情感向量调节**")
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            emo_data['happy'] = st.slider("😆 快乐", 0.0, 1.0, 0.0, key=f"h_{role}")
                            emo_data['sad'] = st.slider("😭 悲伤", 0.0, 1.0, 0.0, key=f"s_{role}")
                            emo_data['angry'] = st.slider("😡 愤怒", 0.0, 1.0, 0.0, key=f"a_{role}")
                        with ec2:
                            emo_data['fear'] = st.slider("😱 恐惧", 0.0, 1.0, 0.0, key=f"f_{role}")
                            emo_data['disgust'] = st.slider("🤢 厌恶", 0.0, 1.0, 0.0, key=f"d_{role}")
                            emo_data['surprise'] = st.slider("😲 惊讶", 0.0, 1.0, 0.0, key=f"su_{role}")
                
                # 保存配置到字典
                config = {
                    "ref_audio_path": ref_path,
                    "emotion_mode": emo_mode,
                    **emo_data # 展开情感数据
                }
                
                # 如果有上传文件，转成 Base64 方便传输 (可选)
                if ref_upload:
                    bytes_data = ref_upload.getvalue()
                    config['ref_file_base64'] = base64.b64encode(bytes_data).decode('utf-8')
                
                role_configs[role] = config

    with col_preview:
        st.subheader("📜 分镜预览")
        with st.container(height=600):
            for item in st.session_state.get('script_data', []):
                st.markdown(f"**[{item['role']}]**: {item['text']}")

    # 3. 合成
    st.divider()
    if st.button("🚀 开始高级合成", type="primary"):
        st.write("正在连接克隆服务...")
        progress = st.progress(0)
        logs = st.expander("运行日志", expanded=True)
        
        for i, item in enumerate(st.session_state['script_data']):
            role = item['role']
            text = item['text']
            
            # 获取当前角色的配置
            cfg = role_configs.get(role, {})
            
            # 调用
            audio, msg = generate_cloned_audio(text, cfg, tts_api_url, global_speed)
            
            if audio:
                st.audio(audio, format="audio/wav")
                st.caption(f"[{role}] {text[:20]}...")
            else:
                logs.error(f"[{role}] 失败: {msg}")
            
            progress.progress((i+1)/len(st.session_state['script_data']))
