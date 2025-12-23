import streamlit as st
import openai

st.set_page_config(page_title="专业文案分镜工具", layout="wide")

# --- 初始化 Session State ---
if 'storyboard_result' not in st.session_state:
    st.session_state.storyboard_result = ""

st.title("🎬 专业电影解说分镜系统")

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ API 配置")
    api_key = st.sidebar.text_input("输入 API Key", type="password")
    base_url = st.sidebar.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.sidebar.text_input("Model ID", value="gpt-4o")
    
    st.markdown("---")
    st.write("### 🤖 分镜准则")
    st.caption("1. 优先保证叙事完整与流畅")
    st.caption("2. 场景/角色切换必须分镜")
    st.caption("3. 建议单行35字左右，但允许根据剧情灵活调整")
    st.caption("4. 严禁改动原文任何字词")

# --- 核心提示词库 ---

# 1. 初始分镜提示词
INITIAL_SEGMENT_PROMPT = """你是一个专业的电影解说分镜师。
任务：将用户提供的文案转化为分镜脚本。
逻辑：
1. 剧情导向：根据场景切换、角色对话、重大动作改变进行分镜。
2. 连贯性：确保每一组分镜在视觉上是连贯的。不要为了断句而断句。
3. 节奏参考：虽然建议每个分镜约5秒（约35字），但如果剧情逻辑需要，可以更长或更短。严禁在句子中间生硬截断导致语义不通。
4. 忠于原文：严禁增减、修改原文中的任何一个字。
5. 格式：
1.分镜内容
2.分镜内容
..."""

# 2. 二次排版整理提示词
REFORMAT_PROMPT = """你是一个分镜排版助手。
任务：用户已经对手动微调了分镜段落，请你重新整理序号。
要求：
1. 观察用户的段落分布，每一行作为一个独立分镜。
2. 严格按照 1. 2. 3. 的顺序重新标注序号。
3. 严禁修改用户段落中的任何文字内容。
4. 确保分镜之间逻辑连贯。"""

# --- 主界面 ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("第一步：上传与生成")
    uploaded_file = st.file_uploader("选择 TXT 文件", type=['txt'])
    
    input_text = ""
    if uploaded_file:
        input_text = uploaded_file.getvalue().decode("utf-8")
        st.text_area("原文预览", input_text, height=200)

    if st.button("🚀 AI 自动分镜"):
        if not api_key or not input_text:
            st.warning("请检查 API Key 和文件内容")
        else:
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            with st.spinner("AI 正在分析剧情..."):
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": INITIAL_SEGMENT_PROMPT},
                        {"role": "user", "content": input_text}
                    ],
                    temperature=0.3
                )
                st.session_state.storyboard_result = response.choices[0].message.content

with col2:
    st.subheader("第二步：人工微调与优化")
    if st.session_state.storyboard_result:
        # 用户在此处手动修改
        edited_text = st.text_area(
            "手动微调（你可以直接修改段落、合并或拆分）", 
            st.session_state.storyboard_result, 
            height=500
        )
        
        if st.button("🔄 重新整理序号 (AI 二次对齐)"):
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            with st.spinner("正在优化序号排版..."):
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": REFORMAT_PROMPT},
                        {"role": "user", "content": edited_text}
                    ],
                    temperature=0.1 # 极低温度保证文字绝不改变
                )
                st.session_state.storyboard_result = response.choices[0].message.content
                st.rerun()

# --- 最终结果导出 ---
if st.session_state.storyboard_result:
    st.markdown("---")
    st.subheader("✅ 最终分镜脚本预览")
    st.code(st.session_state.storyboard_result, language="text")
    st.download_button("📥 下载分镜脚本", st.session_state.storyboard_result, "storyboard_final.txt")
