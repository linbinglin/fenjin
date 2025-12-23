import streamlit as st
from openai import OpenAI
import io
import re

# --- 页面配置 ---
st.set_page_config(page_title="解说分镜工作站-序号增强版", layout="wide")

# --- 1. 初始化状态 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'draft_numbered' not in st.session_state:
    st.session_state.draft_numbered = ""
if 'final_numbered' not in st.session_state:
    st.session_state.final_numbered = ""

st.title("🎬 电影解说·分镜精修工作站 (序号增强版)")
st.markdown("AI初分(带编号) -> 人工自由剪辑 -> 自动重排编号")

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 设置")
    api_key = st.text_input("请输入 API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.divider()
    if st.button("🔄 开启新任务"):
        for key in ['step', 'draft_numbered', 'final_numbered']:
            st.session_state[key] = 1 if key == 'step' else ""
        st.rerun()

def flatten_text(text):
    """彻底抹除原有格式"""
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r'\s+', '', text)
    return text

# ==========================================
# 阶段 1：上传与带编号初分镜
# ==========================================
if st.session_state.step == 1:
    st.header("第一步：上传文案 & 生成带编号初稿")
    uploaded_file = st.file_uploader("选择本地 TXT 文案", type=['txt'])
    
    if uploaded_file:
        raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
        flat_input = flatten_text(raw_text)
        
        if st.button("🚀 生成带编号初稿", type="primary"):
            if not api_key:
                st.error("请配置 API Key")
            else:
                try:
                    with st.spinner("AI 正在解析剧情并生成编号分镜..."):
                        client = OpenAI(api_key=api_key, base_url=base_url)
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": """你是一个优秀的电影解说工作员。
                                任务：阅读文字流，根据剧情逻辑进行分镜。
                                要求：
                                1. **必须包含数字序号**：每一行开头必须以 '数字.' 格式开头（如 1. 2. 3.）。
                                2. **紧凑换行**：每行分镜后直接换行，严禁产生空行，严禁段落隔断。
                                3. 一个分镜对应一个场景或动作，字数建议35字以内。
                                4. 严禁改动、遗漏原文任何一个字。"""},
                                {"role": "user", "content": f"对以下文案进行带编号的紧凑分镜处理：\n\n{flat_input}"}
                            ],
                            temperature=0.3
                        )
                        st.session_state.draft_numbered = response.choices[0].message.content
                        st.session_state.step = 2
                        st.rerun()
                except Exception as e:
                    st.error(f"处理失败：{e}")

# ==========================================
# 阶段 2：人工精修 (带编号编辑)
# ==========================================
elif st.session_state.step == 2:
    st.header("第二步：人工精修 (回车拆分/退格合并)")
    st.info("💡 此时带编号。在需要拆分处按【回车】，在需要合并处按【删除】。合并时若出现多余数字不用管，最后一步会自动清理。")
    
    # 紧凑编辑区
    edited_text = st.text_area(
        "分镜编辑器",
        value=st.session_state.draft_numbered,
        height=500
    )
    
    col2_1, col2_2 = st.columns([1, 5])
    with col2_1:
        if st.button("✅ 确认修改，重编序号", type="primary"):
            st.session_state.draft_numbered = edited_text
            try:
                with st.spinner("正在重新对齐编号..."):
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": """你是一个分镜排版专家。
                            任务：接收用户修改后的文本，清理杂乱编号，按目前的物理换行重新生成 '1.' '2.' '3.' 编号。
                            要求：
                            1. 每一行开头必须有一个数字序号。
                            2. 严格保持用户的换行位置，一行一个号。
                            3. 严禁产生空行，严禁修改原文文字。"""},
                            {"role": "user", "content": edited_text}
                        ],
                        temperature=0.1
                    )
                    st.session_state.final_numbered = response.choices[0].message.content
                    st.session_state.step = 3
                    st.rerun()
            except Exception as e:
                st.error(f"重编失败：{e}")
    with col2_2:
        if st.button("⬅️ 重传文件"):
            st.session_state.step = 1
            st.rerun()

# ==========================================
# 阶段 3：最终产出
# ==========================================
elif st.session_state.step == 3:
    st.header("第三步：最终定稿")
    st.text_area("Final Output", st.session_state.final_numbered, height=500)
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 下载分镜稿", st.session_state.final_numbered, file_name="电影分镜.txt", use_container_width=True)
    with c2:
        if st.button("⬅️ 返回修改", use_container_width=True):
            st.session_state.step = 2
            st.rerun()

st.divider()
st.caption("2025 AI文案分镜工具 | 强制序号重构模式")
