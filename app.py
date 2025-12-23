import streamlit as st
import openai
import re

# 页面配置
st.set_page_config(page_title="流式文案分镜工具", layout="wide")

# --- 自定义样式：让文本框看起来更像分镜表 ---
st.markdown("""
    <style>
    .stTextArea textarea {
        font-family: 'Courier New', Courier, monospace;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 初始化 Session State ---
if 'current_content' not in st.session_state:
    st.session_state.current_content = ""

def renumber_text(text):
    """本地逻辑：将文本按行重新编号，去除原有的乱序编号"""
    # 移除行首已有的数字和点（例如 "1.", "2. ", "10 "）
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # 匹配行首的 数字+点 或 数字+空格 并去掉
        new_line = re.sub(r'^\d+[\.．\s]*', '', line.strip())
        if new_line: # 只保留有内容的行
            cleaned_lines.append(new_line)
    
    # 重新添加连续编号
    return "\n".join([f"{i+1}.{content}" for i, content in enumerate(cleaned_lines)])

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.markdown("---")
    st.write("### ⌨️ 编辑技巧")
    st.info("""
    - **拆分**：在文字中点击鼠标，按【回车】
    - **合并**：在行首按【退格/删除】
    - **整理**：编辑完点下方的“重新对齐编号”
    """)

st.title("🎬 紧凑型分镜编辑器")

# --- 主逻辑 ---
uploaded_file = st.file_uploader("第一步：上传文案 (TXT)", type=['txt'])

if uploaded_file:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    
    if st.button("🚀 AI 初始分镜"):
        if not api_key:
            st.error("请先输入 API Key")
        else:
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            with st.spinner("AI 正在根据剧情深度分镜..."):
                prompt = f"""你是一个电影解说分镜专家。
                任务：将文案拆分为分镜。
                原则：
                1. 场景切换、角色对话、动作改变必须换行。
                2. 保持剧情连贯，不生硬切断句子。
                3. 严禁改动原文任何字词，不增不减。
                4. 格式要求：每一行就是一个分镜，序号开头，行与行之间【严禁】有空行。
                
                原文内容：
                {raw_text}"""
                
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                st.session_state.current_content = response.choices[0].message.content

# --- 编辑区 ---
if st.session_state.current_content:
    st.subheader("第二 step：分镜微调")
    
    # 编辑框
    edited_content = st.text_area(
        "分镜内容 (直接在此处回车拆分或退格合并)", 
        value=st.session_state.current_content, 
        height=500,
        key="main_editor"
    )
    
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("🔄 重新对齐编号"):
            # 使用本地正则逻辑重新排版，不消耗API额度
            st.session_state.current_content = renumber_text(edited_content)
            st.rerun()
            
    with col2:
        st.download_button("📥 导出最终文案", st.session_state.current_content, "final_storyboard.txt")

    st.success("调整提示：修改完文字或段落后，点击‘重新对齐编号’即可自动恢复 1.2.3. 顺序。")
