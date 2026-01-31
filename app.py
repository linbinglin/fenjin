import streamlit as st
import json
import requests
import pandas as pd
from openai import OpenAI

# ==========================================
# 1. 基础配置
# ==========================================
st.set_page_config(layout="wide", page_title="IndexTTS 专业配音台")

if 'script_data' not in st.session_state:
    st.session_state.script_data = None
if 'roles' not in st.session_state:
    st.session_state.roles = []
# 用于存储每个角色的详细配置
if 'role_configs' not in st.session_state:
    st.session_state.role_configs = {}

# ==========================================
# 2. 功能函数
# ==========================================

def call_custom_tts_api(api_url, text, config):
    """
    发送包含克隆参数的复杂请求
    config: 包含 ref_audio_path, emotion_mode, vectors 等的字典
    """
    if not api_url:
        return None, "未配置 API 地址"

    # 构建 Payload (根据常见的 GPT-SoVITS/IndexTTS API 格式构建，可能需要根据你的实际后端微调)
    # 包含了图片中的需求：参考音频、情感模式、情感向量
    payload = {
        "text": text,
        "text_lang": "zh",
        
        # 1. 参考音频 (如果是路径模式)
        "ref_audio_path": config.get("ref_audio_path", ""),
        
        # 2. 情感控制模式
        "emotion_mode": config.get("emotion_mode", "same_as_ref"),
        
        # 3. 情感向量 (只有在选择了向量模式时才生效)
        "emotion_vector": config.get("vectors", {}),
        
        # 其他通用参数
        "speed": 1.0,
        "top_k": 5,
        "top_p": 1.0,
        "temperature": 1.0
    }

    # 如果有上传的文件实体（不仅仅是路径），通常需要用 multipart/form-data 发送
    # 这里为了演示通用性，我们假设后端接受 JSON 路径或者 base64，
    # 或者如果是在本地跑，Streamlit可以通过路径传递。
    # 简单起见，这里演示 JSON 传递参数的方式。
    
    try:
        # 调试：打印发送的数据（开发者看）
        # print("Sending payload:", payload) 
        
        response = requests.post(api_url, json=payload, timeout=120)
        
        if response.status_code == 200:
            return response.content, None
        else:
            return None, f"API 报错 ({response.status_code}): {response.text}"
    except Exception as e:
        return None, f"网络请求失败: {str(e)}"

def analyze_script(text, api_key, model):
    """LLM 角色拆分逻辑"""
    client = OpenAI(api_key=api_key, base_url="https://yunwu.ai/v1")
    prompt = f"""
    请将小说拆分为[{{"role": "角色", "text": "对白"}}]的JSON列表。
    只输出JSON，无Markdown。
    文本：{text[:3000]}
    """
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(resp.choices[0].message.content.replace("```json", "").replace("```", ""))
    except Exception as e:
        if isinstance(e, dict) and 'script' in e: return e['script'] # 容错
        st.error(f"LLM分析错: {e}")
        return []

# ==========================================
# 3. 侧边栏设置
# ==========================================
with st.sidebar:
    st.header("⚙️ 全局配置")
    yunwu_key = st.text_input("Yunwu API Key", type="password")
    llm_model = st.selectbox("分角模型", ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet", "doubao-pro-32k"])
    
    st.divider()
    
    st.subheader("🔊 TTS 接口设置")
    tts_url = st.text_input("API 地址", value="http://127.0.0.1:9880/tts_endpoint",help="指向你部署的 IndexTTS/GPT-SoVITS 推理接口")
    
    st.info("提示：图片中的功能需要后端 API 支持接收 `emotion_vector` 和 `ref_audio` 参数。")
    
    st.divider()
    txt_file = st.file_uploader("导入剧本 TXT", type="txt")

# ==========================================
# 4. 主界面
# ==========================================
st.title("🎛️ IndexTTS 深度克隆配音台")

# --- 步骤1：文本分析 ---
if txt_file and yunwu_key:
    if st.button("🚀 1. 拆分角色与对白"):
        raw_text = txt_file.getvalue().decode("utf-8")
        res = analyze_script(raw_text, yunwu_key, llm_model)
        
        # 兼容处理返回格式
        final_list = []
        if isinstance(res, dict):
            # 尝试找 list 类型的 value
            for v in res.values():
                if isinstance(v, list): final_list = v; break
        elif isinstance(res, list):
            final_list = res
            
        if final_list:
            st.session_state.script_data = final_list
            st.session_state.roles = list(set([x['role'] for x in final_list]))
            st.success(f"成功识别 {len(st.session_state.roles)} 个角色！")
        else:
            st.error("未能识别出有效的分镜数据，请检查 LLM 返回。")

# --- 步骤2：复杂角色配置 (仿图片UI) ---
if st.session_state.script_data:
    col_config, col_preview = st.columns([1.2, 1.8], gap="large")
    
    with col_config:
        st.subheader("🎚️ 角色音色克隆面板")
        st.markdown("在这里为每个角色配置独立的参考音频和情感。")
        
        # 遍历所有角色，生成配置卡片
        for role in st.session_state.roles:
            # 使用 expander 模拟卡片效果
            with st.expander(f"👤 设置：{role}", expanded=False):
                
                # 初始化该角色的配置字典
                if role not in st.session_state.role_configs:
                    st.session_state.role_configs[role] = {}
                
                # 1. 参考音频设置 (模仿图片中的 "参考音频")
                st.markdown("#### 1. 参考音频 (Reference)")
                # 方式A: 输入服务器上的绝对路径 (适合本地部署)
                ref_path = st.text_input("参考音频路径 (.wav)", 
                                       value=f"D:/models/ref_audio/{role}.wav", 
                                       key=f"path_{role}",
                                       help="填入运行 TTS 那个电脑上的文件绝对路径")
                
                # 方式B: 直接上传 (适合云端, 需要后端支持文件接收)
                # uploaded_ref = st.file_uploader("或上传音频文件", type=["wav", "mp3"], key=f"file_{role}")
                
                st.session_state.role_configs[role]['ref_audio_path'] = ref_path

                st.divider()

                # 2. 情感控制 (模仿图片中的 "情感控制")
                st.markdown("#### 2. 情感控制 (Emotion)")
                emotion_mode = st.selectbox(
                    "控制模式", 
                    options=["与参考音频相同", "使用情感向量", "使用文本描述"],
                    key=f"emm_{role}"
                )
                st.session_state.role_configs[role]['emotion_mode'] = emotion_mode

                # 3. 情感向量滑块 (只有选中"使用情感向量"才显示，模仿图片下方的滑块)
                if emotion_mode == "使用情感向量":
                    st.caption("调整各维度的情感权重 (0.0 - 1.0)")
                    c1, c2 = st.columns(2)
                    
                    vectors = {}
                    with c1:
                        vectors['happy'] = st.slider("快乐 (Happy)", 0.0, 1.0, 0.0, 0.1, key=f"hap_{role}")
                        vectors['angry'] = st.slider("愤怒 (Angry)", 0.0, 1.0, 0.0, 0.1, key=f"ang_{role}")
                        vectors['sad'] = st.slider("悲伤 (Sad)", 0.0, 1.0, 0.0, 0.1, key=f"sad_{role}")
                    with c2:
                        vectors['fear'] = st.slider("恐惧 (Fear)", 0.0, 1.0, 0.0, 0.1, key=f"fea_{role}")
                        vectors['disgust'] = st.slider("厌恶 (Disgust)", 0.0, 1.0, 0.0, 0.1, key=f"dis_{role}")
                        vectors['depressed'] = st.slider("忧郁 (Depressed)", 0.0, 1.0, 0.0, 0.1, key=f"dep_{role}")
                    
                    st.session_state.role_configs[role]['vectors'] = vectors

    # --- 步骤3：右侧预览与合成 ---
    with col_preview:
        st.subheader("▶️ 分镜合成预览")
        
        # 批量合成按钮
        if st.button("🎵 合成页面所有台词", type="primary"):
            st.toast("正在发送批量请求...")

        script_container = st.container(height=800)
        with script_container:
            for idx, item in enumerate(st.session_state.script_data):
                role = item['role']
                text = item['text']
                
                # 不同角色不同背景色
                bg_color = "#f4f4f4" if role == "旁白" else "#e1f5fe"
                border_color = "#999" if role == "旁白" else "#0288d1"
                
                st.markdown(
                    f"""
                    <div style="
                        background-color: {bg_color}; 
                        border-left: 5px solid {border_color};
                        padding: 12px; 
                        border-radius: 4px; 
                        margin-bottom: 8px;">
                        <span style="font-weight:bold; color:{border_color}">{role}</span>
                        <div style="margin-top:4px; font-size:16px;">{text}</div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

                col_act, col_info = st.columns([1, 4])
                
                # 生成按钮
                if col_act.button("🔊 生成", key=f"gen_{idx}"):
                    # 获取当前角色的最新配置
                    current_config = st.session_state.role_configs.get(role, {})
                    
                    with st.spinner(f"正在以【{role}】的参数合成..."):
                        audio_data, err = call_custom_tts_api(tts_url, text, current_config)
                        
                        if audio_data:
                            st.audio(audio_data, format="audio/wav")
                        else:
                            st.error(err)
                            st.json(current_config) # 出错时显示当前用的配置方便调试

else:
    st.info("👈 请先在左侧上传剧本文件")
