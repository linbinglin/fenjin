import streamlit as st
import openai
import json
import asyncio
import edge_tts
import os
import tempfile

# --- 页面配置 ---
st.set_page_config(page_title="AI 智能分角配音助手", layout="wide")

# --- 自定义 CSS 样式，模仿截图中的卡片风格 ---
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
    .role-label {
        font-weight: bold;
        color: #555;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 会话状态初始化 ---
if 'script_data' not in st.session_state:
    st.session_state.script_data = [] # 存储分角后的剧本
if 'roles' not in st.session_state:
    st.session_state.roles = set()    # 存储所有角色
if 'role_voice_map' not in st.session_state:
    st.session_state.role_voice_map = {} # 存储角色与声音的对应关系

# --- 侧边栏：设置 ---
st.sidebar.title("🛠️ 设置面板")

st.sidebar.subheader("1. 模型接口设置")
base_url = st.sidebar.text_input("API Base URL", value="https://yunwu.ai/v1/")
api_key = st.sidebar.text_input("API Key", type="password", help="请输入你的 API Key")

# 模型选择列表
model_options = [
    "deepseek-chat",
    "gpt-4o",
    "claude-3-5-sonnet-20240620",
    "gemini-1.5-pro",
    "grok-beta",
    "doubao-pro-4k"
]
selected_model = st.sidebar.selectbox("选择 AI 模型", model_options + ["自定义..."])
if selected_model == "自定义...":
    selected_model = st.sidebar.text_input("输入自定义模型名称")

st.sidebar.subheader("2. 配音设置")
# 这里列出一些 Edge-TTS 常用中文音色
voice_options = {
    "云希 (男神音)": "zh-CN-YunxiNeural",
    "晓晓 (活泼女声)": "zh-CN-XiaoxiaoNeural",
    "云健 (体育男声)": "zh-CN-YunjianNeural",
    "辽宁 (东北老铁)": "zh-CN-liaoning-XiaobeiNeural",
    "陕西 (方言)": "zh-CN-shaanxi-XiaoniNeural",
    "云扬 (新闻男声)": "zh-CN-YunyangNeural",
    "晓伊 (温柔女声)": "zh-CN-XiaoyiNeural"
}

# --- 核心功能函数 ---

def parse_script_with_ai(text, api_key, base_url, model):
    """调用大模型进行分角识别"""
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

async def generate_audio_edge(text, voice, output_file):
    """
    调用 Edge-TTS 生成音频。
    如果你有私有的 indextts2 API，可以在这里替换代码。
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

# --- 主界面 ---

st.title("🎙️ AI 剧本分角与配音系统")

# 1. 文件上传
uploaded_file = st.file_uploader("📂 第一步：上传 TXT 剧本文件", type=["txt"])

if uploaded_file is not None:
    # 读取文件内容
    stringio = uploaded_file.getvalue().decode("utf-8")
    
    # 显示原始内容预览
    with st.expander("查看原始文本"):
        st.text_area("原始内容", stringio, height=150)
    
    # 2. AI 分角按钮
    if st.button("🤖 开始 AI 角色识别"):
        if not api_key:
            st.warning("请先在左侧侧边栏输入 API Key！")
        else:
            result = parse_script_with_ai(stringio, api_key, base_url, selected_model)
            if result:
                st.session_state.script_data = result
                # 提取所有角色
                roles = set(item['role'] for item in result)
                st.session_state.roles = roles
                st.success(f"识别成功！共发现 {len(roles)} 个角色。")

# 3. 角色配音设置
if st.session_state.script_data:
    st.divider()
    st.header("🎭 第二步：角色配音设置")
    
    cols = st.columns(3)
    # 为每个角色分配声音
    for i, role in enumerate(st.session_state.roles):
        with cols[i % 3]:
            st.markdown(f"**{role}**")
            # 默认分配
            default_idx = 0
            if role == "旁白":
                default_idx = 5 # 新闻男声
            elif role in ["系统", "火冥"]:
                default_idx = 2
            
            selected_voice_name = st.selectbox(
                f"选择音色", 
                options=list(voice_options.keys()),
                key=f"voice_{role}",
                index=default_idx
            )
            st.session_state.role_voice_map[role] = voice_options[selected_voice_name]

    # 4. 显示分镜预览与生成
    st.divider()
    st.header("🎬 第三步：分镜预览与合成")
    
    # 显示类似截图的分镜列表
    for idx, item in enumerate(st.session_state.script_data):
        role = item['role']
        text = item['text']
        
        # 渲染卡片
        col1, col2 = st.columns([1, 5])
        with col1:
            st.info(f"👤 {role}")
        with col2:
            st.markdown(f'<div class="text-content">{text}</div>', unsafe_allow_html=True)
    
    # 合成按钮
    if st.button("🎧 开始生成配音 (调用 TTS)"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        audio_results = []
        
        temp_dir = tempfile.mkdtemp()
        
        total_lines = len(st.session_state.script_data)
        
        for i, item in enumerate(st.session_state.script_data):
            role = item['role']
            text = item['text']
            voice = st.session_state.role_voice_map.get(role, "zh-CN-XiaoxiaoNeural")
            
            status_text.text(f"正在生成 ({i+1}/{total_lines}): {role} - {text[:10]}...")
            
            # 生成文件名
            filename = f"{i:03d}_{role}.mp3"
            filepath = os.path.join(temp_dir, filename)
            
            # 异步调用 TTS
            try:
                asyncio.run(generate_audio_edge(text, voice, filepath))
                audio_results.append({
                    "role": role,
                    "text": text,
                    "file": filepath
                })
            except Exception as e:
                st.error(f"生成失败: {str(e)}")
            
            progress_bar.progress((i + 1) / total_lines)
            
        status_text.text("✅ 所有配音生成完毕！")
        
        # 5. 展示结果
        st.subheader("播放列表")
        for audio in audio_results:
            st.markdown(f"**{audio['role']}**: {audio['text']}")
            st.audio(audio['file'])
            
            # 这里如果你想提供打包下载，可以使用 zipfile 库打包 temp_dir 下的文件
