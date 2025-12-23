import streamlit as st
from openai import OpenAI
import io
import re

# --- 页面配置 ---
st.set_page_config(page_title="半自动分镜工作站", layout="wide")

st.title("🎬 电影解说·半自动分镜工作站")
st.markdown("先由 AI 进行逻辑初分，再由你手动精修，最后 AI 自动重新编号。")

# --- 初始化状态机 ---
if 'step' not in st.session_state:
    st.session_state.step = 1  # 1: 上传, 2: AI初分及人工精修, 3: 最终输出
if 'draft_content' not in st.session_state:
    st.session_state.draft_content = ""
if 'final_content' not in st.session_state:
    st.session_state.final_content = ""

# --- 侧边栏配置 ---
with st.sidebar:
    st.title("⚙️ 配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    if st.button("🔄 开启新任务"):
        st.session_state.step = 1
        st.session_state.draft_content = ""
        st.session_state.final_content = ""
        st.rerun()

# --- 辅助函数 ---
def clean_text(text):
    """消除所有原有段落"""
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r'\s+', '', text)
    return text

# --- 阶段 1：上传与初分 ---
if st.session_state.step == 1:
    uploaded_file = st.file_uploader("上传文案 (.txt)", type=['txt'])
    if uploaded_file:
        raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
        flat_text = clean_text(raw_text)
        
        st.info("已完成文本清洗，点击下方按钮由 AI 进行初步剧情拆解。")
        if st.button("🚀 生成初版分镜 (Step 1)"):
            if not api_key:
                st.error("请输入 API Key")
            else:
                try:
                    with st.spinner("AI 正在解析剧情逻辑..."):
                        client = OpenAI(api_key=api_key, base_url=base_url)
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": "你是一个电影分镜导演。请阅读以下没有段落的文字流，按照视觉剧情进行分镜。每行一个分镜，以'数字.'开头。严禁漏字，严禁改字。"},
                                {"role": "user", "content": flat_text}
                            ],
                            temperature=0.3
                        )
                        st.session_state.draft_content = response.choices[0].message.content
                        st.session_state.step = 2
                        st.rerun()
                except Exception as e:
                    st.error(f"出错：{e}")

# --- 阶段 2：人工精修 ---
elif st.session_state.step == 2:
    st.subheader("✍️ 人工精修区")
    st.markdown("""
    **操作指南：**
    - **合并分镜**：删除换行符，让两段话合并到一行。
    - **拆分分镜**：在需要断开的地方按下回车键。
    - **字数参考**：你可以自由控制每行长度，AI 稍后会自动重新编号。
    """)
    
    # 用户在这里手动编辑
    user_edited = st.text_area(
        "请在此直接修改文案分段（无需担心数字编号，重点关注在哪里分镜）：",
        value=st.session_state.draft_content,
        height=500
    )
    
    if st.button("✅ 我已完成精修，生成最终编号 (Step 2)"):
        st.session_state.draft_content = user_edited
        try:
            with st.spinner("正在重新格式化并排序..."):
                client = OpenAI(api_key=api_key, base_url=base_url)
                # 第二遍分镜的 Prompt：极其严格的重排序指令
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": """你是一个严格的文案格式化助手。
                        你的唯一任务是：
                        1. 接收用户精修后的文本。
                        2. 按照用户现在的分段（换行符），重新从 1 开始进行数字编号。
                        3. **绝对严禁**合并用户已经分开的行，也**绝对严禁**拆分用户已经合并的行。
                        4. **绝对严禁**修改、增加或删除原文中的任何一个字。
                        5. 确保每行格式为：'数字.内容'。"""},
                        {"role": "user", "content": user_edited}
                    ],
                    temperature=0.1 # 极低随机性，确保不自作聪明
                )
                st.session_state.final_content = response.choices[0].message.content
                st.session_state.step = 3
                st.rerun()
        except Exception as e:
            st.error(f"排序出错：{e}")

# --- 阶段 3：最终结果与下载 ---
elif st.session_state.step == 3:
    st.subheader("🎬 最终分镜定稿")
    
    # 展示并允许最后查看
    st.text_area("最终分镜内容", st.session_state.final_content, height=500)
    
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "📥 下载最终分镜 TXT",
            st.session_state.final_content,
            file_name="最终分镜稿.txt",
            use_container_width=True
        )
    with col2:
        if st.button("⬅️ 返回修改", use_container_width=True):
            st.session_state.step = 2
            st.rerun()

# --- 界面增强 ---
st.divider()
st.caption("流程：1. AI 暴力拆解剧情 -> 2. 人类直觉微调分段 -> 3. AI 重新对齐编号。")
