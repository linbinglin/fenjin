import streamlit as st
from openai import OpenAI
import io
import re

# --- 页面配置 ---
st.set_page_config(page_title="极速分镜编辑器", layout="wide")

# --- 初始化状态机 ---
if 'step' not in st.session_state:
    st.session_state.step = 1 
if 'editor_content' not in st.session_state:
    st.session_state.editor_content = ""
if 'final_numbered_content' not in st.session_state:
    st.session_state.final_numbered_content = ""

st.title("🎬 极速文案分镜编辑器")
st.markdown("AI初分 -> 人工回车/合并 -> 自动编号")

# --- 侧边栏配置 ---
with st.sidebar:
    st.title("⚙️ API 设置")
    api_key = st.sidebar.text_input("请输入 API Key", type="password")
    base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.sidebar.text_input("Model ID", value="gpt-4o")
    
    st.divider()
    if st.button("🔄 开启新任务"):
        for key in ['step', 'editor_content', 'final_numbered_content']:
            st.session_state[key] = 1 if key == 'step' else ""
        st.rerun()

# --- 逻辑处理函数 ---
def flatten_text(text):
    """彻底清除所有原有换行和空格，变成纯字符流"""
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r'\s+', '', text)
    return text

# --- 阶段 1：上传并进行“无编号”初分 ---
if st.session_state.step == 1:
    uploaded_file = st.file_uploader("第一步：选择本地 TXT 文案", type=['txt'])
    if uploaded_file:
        raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
        flat_text = flatten_text(raw_text)
        
        if st.button("🚀 生成初步分镜"):
            if not api_key:
                st.error("请先输入 API Key")
            else:
                try:
                    with st.spinner("AI 正在根据剧情逻辑拆解分镜..."):
                        client = OpenAI(api_key=api_key, base_url=base_url)
                        # 重要：强制 AI 不要输出编号
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": """你是一个专业的电影分镜导演。
                                任务：阅读文字流，根据剧情逻辑进行分镜。
                                要求：
                                1. 每个分镜占一行（即在分镜处换行）。
                                2. 严禁输出任何数字编号、符号、前缀。
                                3. 严禁修改、遗漏、添加原文任何文字。
                                4. 只输出纯文案换行后的结果。"""},
                                {"role": "user", "content": f"请对以下文案进行逻辑换行：\n\n{flat_text}"}
                            ],
                            temperature=0.3
                        )
                        st.session_state.editor_content = response.choices[0].message.content
                        st.session_state.step = 2
                        st.rerun()
                except Exception as e:
                    st.error(f"处理失败：{e}")

# --- 阶段 2：人工极速编辑 (回车拆分/退格合并) ---
elif st.session_state.step == 2:
    st.subheader("✍️ 人工精修 (回车拆分 / 退格合并)")
    st.info("💡 操作提示：AI 已为你做了初步换行。现在你可以：在需要分段处按【Enter回车】，在需要合并处按【Backspace退格】。无需管数字。")
    
    # 纯净的编辑区
    user_edited = st.text_area(
        "分镜编辑窗口",
        value=st.session_state.editor_content,
        height=500,
        label_visibility="collapsed"
    )
    
    if st.button("✅ 调整好了，生成最终编号"):
        st.session_state.editor_content = user_edited
        try:
            with st.spinner("正在自动编号并校验..."):
                client = OpenAI(api_key=api_key, base_url=base_url)
                # 第三步：只负责数行数并加编号
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": """你是一个严格的编号助手。
                        任务：接收文本，在每一行开头加上数字编号（如 1. 2. 3.）。
                        要求：
                        1. 严格按照用户现在的换行位置，一行就是一个编号。
                        2. 绝对不能合并行，绝对不能拆分行。
                        3. 绝对不能更改原文任何字。"""},
                        {"role": "user", "content": user_edited}
                    ],
                    temperature=0.1
                )
                st.session_state.final_numbered_content = response.choices[0].message.content
                st.session_state.step = 3
                st.rerun()
        except Exception as e:
            st.error(f"编号失败：{e}")

# --- 阶段 3：最终产出 ---
elif st.session_state.step == 3:
    st.subheader("🎬 最终分镜稿")
    st.text_area("最终结果", st.session_state.final_numbered_content, height=500)
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 下载分镜 TXT", st.session_state.final_numbered_content, file_name="分镜结果.txt")
    with c2:
        if st.button("⬅️ 回去微调"):
            st.session_state.step = 2
            st.rerun()

st.divider()
st.caption("2025 AI文案分镜工具 · 逻辑：强制去段落 -> 视觉逻辑初分 -> 人工自由剪辑 -> 自动编号排版")
