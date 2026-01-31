import streamlit as st
import json
import requests
from openai import OpenAI

# ==========================================
# 1. 页面初始化
# ==========================================
st.set_page_config(layout="wide", page_title="AI 配音工作台 (Yunwu + IndexTTS)")

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
    """
    第一步：调用 LLM API 进行角色拆分
    严格使用 https://yunwu.ai/v1/ 接口
    """
    # 【重点 1】这里强制指定了第三方中转地址
    client = OpenAI(
        api_key=api_key,
        base_url="https://yunwu.ai/v1" 
    )

    prompt = f"""
    你是一个专业的配音导演。请将以下小说/剧本片段拆分为标准的分镜脚本。
    
    【要求】
    1. 识别每一句话的角色（旁白、具体人名）。
    2. 输出必须是严格的 JSON 格式列表：[{{"role": "角色名", "text": "对白内容"}}, ...]
    3. 不要输出任何Markdown标记（如 ```json），只输出纯文本 JSON。
    
    【文本内容】
    {text[:4000]}
    """

    try:
        response = client.chat.completions.create(
            model=model_id, # 使用用户选择的模型ID
            messages=[
                {"role": "system", "content": "你是一个JSON输出助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        content = response.choices[0].message.content
        # 清洗数据，防止模型偶尔吐出 markdown
        content = content.replace("```json", "").replace("```", "")
        return json.loads(content)
    except Exception as e:
        return f"Error: {e}"

def call_indextts_api(api_url, text, config):
    """
    第二步：调用 IndexTTS 接口进行配音
    支持传递参考音频路径和情感向量
    """
    if not api_url:
        return None, "请在侧边栏填写 IndexTTS API 地址"

    # 构建高级请求参数 (包含克隆和情感)
    payload = {
        "text": text,
        "text_lang": "zh",
        # 读取配置中的参考音频路径
        "ref_audio_path": config.get("ref_audio_path", ""),
        # 读取配置中的情感模式
        "emotion_mode": config.get("emotion_mode", "same_as_ref"),
        # 读取配置中的情感向量
        "emotion_vector": config.get("vectors", {}),
        # 基础参数
        "speed": 1.0
    }
    
    try:
        # 发送请求
        resp = requests.post(api_url, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.content, None
        else:
            return None, f"TTS服务端报错: {resp.text}"
    except Exception as e:
        return None, f"请求异常: {e}"

# ==========================================
# 3. 侧边栏：配置中心
# ==========================================
with st.sidebar:
    st.header("⚙️ 核心配置")
    
    with st.expander("🤖 1. LLM 模型设置", expanded=True):
        st.markdown("**接口地址**: `https://yunwu.ai/v1/` (已内置)")
        
        # API Key 输入
        user_api_key = st.text_input("请输入 Yunwu API Key", type="password")
        
        # 【重点 2】模型选择下拉菜单 (满足要求3)
        # 这里的 value 对应 api 调用时的 model 参数
        model_selection = st.selectbox(
            "选择 AI 模型",
            options=[
                "deepseek-chat",        # DeepSeek V3
                "gpt-4o",               # GPT-4o
                "claude-3-5-sonnet",    # Claude 3.5
                "gemini-pro",           # Gemini
                "grok-beta",            # Grok
                "doubao-pro-32k",       # 豆包
            ],
            index=0,
            help="选择用于分析剧本角色的模型"
        )

    with st.expander("🔊 2. IndexTTS 设置", expanded=True):
        tts_api_input = st.text_input(
            "IndexTTS API 地址", 
            value="http://127.0.0.1:9880/tts",
            help="本地部署请填本地地址，云端运行请填 Ngrok 公网地址"
        )
        st.caption("提示：请确保后端支持 JSON 格式接收 ref_audio_path 参数")

    st.markdown("---")
    st.header("📂 文件操作")
    # 【重点 1】本地文件选择
    uploaded_file = st.file_uploader("导入小说/剧本 TXT", type="txt")

# ==========================================
# 4. 主界面逻辑
# ==========================================
st.title("🎙️ 智能配音工作台")

# --- 步骤 1：LLM 识别 ---
if uploaded_file and user_api_key:
    # 读取文件
    script_text = uploaded_file.getvalue().decode("utf-8")
    
    if st.button(f"🚀 使用 {model_selection} 分析剧本角色", type="primary"):
        with st.spinner("正在请求 Yunwu.ai 进行角色拆分..."):
            result = analyze_script_llm(script_text, user_api_key, model_selection)
            
            if isinstance(result, list):
                st.session_state.script_data = result
                st.session_state.roles = list(set([x['role'] for x in result]))
                st.success("✅ 角色拆分成功！")
            else:
                st.error(f"分析失败: {result}")

# --- 步骤 2：配音设置与生成 ---
if st.session_state.script_data:
    col_setup, col_preview = st.columns([1.5, 2], gap="medium")
    
    # === 左侧：高级角色配置 (仿截图 UI) ===
    with col_setup:
        st.subheader("🎛️ 角色克隆配置")
        st.info("为每个角色配置独立的参考音频和情感")
        
        for role in st.session_state.roles:
            # 初始化配置
            if role not in st.session_state.role_configs:
                st.session_state.role_configs[role] = {}

            # 使用 expander 收纳每个角色的面板
            with st.expander(f"👤 {role} 设置", expanded=False):
                # 1. 填入参考音频路径
                ref_path = st.text_input(
                    "参考音频路径 (Ref Audio Path)", 
                    value=f"D:/Data/wavs/{role}.wav", 
                    key=f"path_{role}",
                    help="TTS 服务器上的绝对路径"
                )
                
                # 2. 情感模式选择
                emo_mode = st.selectbox(
                    "情感控制模式", 
                    ["与参考音频相同", "使用情感向量", "使用文本描述"], 
                    key=f"emo_{role}"
                )
                
                st.session_state.role_configs[role]['ref_audio_path'] = ref_path
                st.session_state.role_configs[role]['emotion_mode'] = emo_mode
                
                # 3. 情感向量 (只有选向量模式才显示)
                if emo_mode == "使用情感向量":
                    st.caption("情感混合 (0.0 - 1.0)")
                    c1, c2 = st.columns(2)
                    vecs = {}
                    vecs['happy'] = c1.slider("😊 快乐", 0.0, 1.0, 0.0, key=f"hap_{role}")
                    vecs['angry'] = c1.slider("😡 愤怒", 0.0, 1.0, 0.0, key=f"ang_{role}")
                    vecs['sad'] = c1.slider("😢 悲伤", 0.0, 1.0, 0.0, key=f"sad_{role}")
                    
                    vecs['fear'] = c2.slider("😱 恐惧", 0.0, 1.0, 0.0, key=f"fea_{role}")
                    vecs['disgust'] = c2.slider("🤢 厌恶", 0.0, 1.0, 0.0, key=f"dis_{role}")
                    vecs['surprise'] = c2.slider("😲 惊讶", 0.0, 1.0, 0.0, key=f"sur_{role}")
                    
                    st.session_state.role_configs[role]['vectors'] = vecs

    # === 右侧：分镜预览与合成 ===
    with col_preview:
        st.subheader("📜 分镜合成预览")
        
        # 容器包含所有台词
        container = st.container(height=800)
        with container:
            for i, line in enumerate(st.session_state.script_data):
                role_name = line['role']
                content = line['text']
                
                # 简单的样式区分
                is_aside = role_name in ["旁白", "系统"]
                color_style = "background:#f9f9f9;border-left:4px solid #aaa;" if is_aside else "background:#eef6ff;border-left:4px solid #4da6ff;"
                
                st.markdown(
                    f"""
                    <div style="{color_style} padding:10px; border-radius:5px; margin-bottom:5px;">
                        <small style="font-weight:bold; color:#555">{role_name}</small><br>
                        <span style="font-size:16px;">{content}</span>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                # 按钮行
                cols = st.columns([1, 4])
                if cols[0].button("▶️ 生成", key=f"gen_{i}"):
                    # 获取该角色当前的配置
                    curr_conf = st.session_state.role_configs.get(role_name, {})
                    
                    with st.spinner("生成中..."):
                        audio_data, err_msg = call_indextts_api(tts_api_input, content, curr_conf)
                        
                        if audio_data:
                            st.audio(audio_data, format="audio/wav")
                        else:
                            st.error(err_msg)
                            # 调试显示当前发送的配置
                            st.json(curr_conf)
else:
    if not uploaded_file:
        st.info("👈 请先在左侧上传文件")
