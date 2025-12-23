import streamlit as st
import openai
import re

# 页面配置
st.set_page_config(page_title="智能文案深度分镜", layout="wide")

# --- 辅助函数 ---

def pre_process_text(text):
    """
    预处理：抹掉原文所有换行，防止AI参考原段落偷懒
    """
    # 替换掉所有换行符、制表符
    cleaned = re.sub(r'[\r\n\t]+', '', text)
    # 压缩多余空格
    cleaned = re.sub(r'\s+', '', cleaned)
    return cleaned

def renumber_text(text):
    """
    本地逻辑：重新对用户修改后的分镜进行 1.2.3. 编号
    """
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # 移除行首已有的任何数字编号和特殊符号
        new_line = re.sub(r'^\d+[\.．\s、\-]*', '', line.strip())
        if new_line:
            cleaned_lines.append(new_line)
    return "\n".join([f"{i+1}.{content}" for i, content in enumerate(cleaned_lines)])

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 系统配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.markdown("---")
    st.write("### 🎬 分镜逻辑设定")
    st.caption("1. 系统会自动抹除原文段落，强制AI深度理解。")
    st.caption("2. 分镜触发：场景/对话/动作切换。")
    st.caption("3. 字数：35字左右为参考，逻辑完整优先。")

# --- 主界面 ---
st.title("🎞️ 电影解说文案深度分镜工具")

if 'storyboard_data' not in st.session_state:
    st.session_state.storyboard_data = ""

uploaded_file = st.file_uploader("第一步：上传文案 (TXT)", type=['txt'])

if uploaded_file:
    original_content = uploaded_file.getvalue().decode("utf-8")
    
    if st.button("🚀 开始深度逻辑分镜"):
        if not api_key:
            st.error("请在侧边栏配置 API Key")
        else:
            # 执行数据清洗：让AI无从参考原段落
            clean_input = pre_process_text(original_content)
            
            client = openai.OpenAI(api_key=api_key, base_url=base_url)
            with st.spinner("AI 正在解析视觉逻辑并划分分镜..."):
                prompt = f"""你是一个优秀的电影解说工作员，请对以下无格式文案进行深度剧情分析并分镜。

【重要前提】：
我已将原文的段落格式全部抹除，请你根据文字描绘的视觉逻辑重新划分。

【分镜准则】：
1. 剧情导向：严格根据场景转换、角色对话切换、动作画面改变来设定下一个分镜。
2. 文本完整：不遗漏、不增减、不修改原文中的任何一个字。
3. 节奏控制：每个分镜内容不宜过长，参考长度为35字左右（约5秒音频），但请务必保证句子完整，不要在主谓宾中间生硬截断。
4. 连贯流畅：让分镜转场符合电影解说的叙事节奏。

【输出格式】：
1.内容
2.内容
3.内容
（注意：行与行之间不要留空行）

【待处理文案】：
{clean_input}"""

                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                st.session_state.storyboard_data = response.choices[0].message.content

# --- 编辑与微调区 ---
if st.session_state.storyboard_data:
    st.markdown("---")
    st.subheader("第二步：分镜手动微调")
    st.info("💡 操作指南：直接在下方框内【回车】拆分分镜，或【退格】合并分镜。修改完后点击“刷新编号”即可。")
    
    # 编辑文本框
    user_edited = st.text_area(
        "分镜编辑器", 
        value=st.session_state.storyboard_data, 
        height=500,
        key="editor"
    )
    
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        if st.button("🔄 刷新数字编号"):
            st.session_state.storyboard_data = renumber_text(user_edited)
            st.rerun()
    with c2:
        st.download_button("📥 导出分镜稿", st.session_state.storyboard_data, "final_storyboard.txt")
