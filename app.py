import streamlit as st
from openai import OpenAI
import io
import re

# --- 页面配置 ---
st.set_page_config(page_title="极简分镜编辑器", layout="wide")

# --- 初始化状态 ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'editor_content' not in st.session_state:
    st.session_state.editor_content = ""
if 'final_numbered' not in st.session_state:
    st.session_state.final_numbered = ""

st.title("🎬 极简分镜工作站")
st.markdown("AI 初分镜 -> 人工回车拆分/退格合并 -> AI 自动重编序号")

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 配置")
    api_key = st.text_input("请输入 API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o", help="请输入模型名称，如 gpt-4o, deepseek-chat 等")
    
    st.divider()
    if st.button("🔄 开启新任务"):
        for key in ['step', 'editor_content', 'final_numbered']:
            st.session_state[key] = 1 if key == 'step' else ""
        st.rerun()

def flatten_text(text):
    """彻底抹除段落，变成单行文字流"""
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r'\s+', '', text)
    return text

# ==========================================
# 阶段 1：上传与紧凑初分
# ==========================================
if st.session_state.step == 1:
    uploaded_file = st.file_uploader("选择本地 TXT 文案", type=['txt'])
    if uploaded_file:
        raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
        flat_input = flatten_text(raw_text)
        
        if st.button("🚀 生成初步分镜 (带编号)", type="primary"):
            if not api_key:
                st.error("请先配置 API Key")
            else:
                try:
                    with st.spinner("AI 正在解析剧情..."):
                        client = OpenAI(api_key=api_key, base_url=base_url)
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": """你是一个优秀的电影解说工作员。
                                任务：阅读文字流，根据剧情逻辑进行分镜。
                                要求：
                                1. 每一行开头必须有数字编号（如 1. 2. 3.）。
                                2. **极致紧凑**：每行分镜后直接换行，严禁在两行之间产生任何空行或额外段落。
                                3. 严禁修改、遗漏或添加原文文字。
                                4. 输出示例：
                                1.分镜内容A
                                2.分镜内容B
                                3.分镜内容C"""},
                                {"role": "user", "content": f"对以下文案进行紧凑分镜处理：\n\n{flat_input}"}
                            ],
                            temperature=0.3
                        )
                        st.session_state.editor_content = response.choices[0].message.content
                        st.session_state.step = 2
                        st.rerun()
                except Exception as e:
                    st.error(f"处理失败：{e}")

# ==========================================
# 阶段 2：人工精修 (极简编辑)
# ==========================================
elif st.session_state.step == 2:
    st.subheader("✍️ 分镜微调")
    st.info("💡 键盘操作：在需要拆分处按【回车 Enter】，在需要合并处按【删除 Backspace】。无需手动改数字。")
    
    # 核心编辑区：紧凑展示
    edited_text = st.text_area(
        "内容编辑区（紧凑模式）",
        value=st.session_state.editor_content,
        height=500,
        label_visibility="collapsed"
    )
    
    if st.button("✅ 调整完毕，重新生成标准编号"):
        st.session_state.editor_content = edited_text
        try:
            with st.spinner("正在标准化编号..."):
                client = OpenAI(api_key=api_key, base_url=base_url)
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": """你是一个严格的分镜重编助手。
                        任务：按照用户现在的换行结构，重新从1开始编号。
                        要求：
                        1. 每一行就是一个分镜，每一行开头加'数字.'。
                        2. **严禁产生空行**，所有行必须紧密相连。
                        3. 绝对不改原文文字，只负责清理旧编号并加新编号。"""},
                        {"role": "user", "content": edited_text}
                    ],
                    temperature=0.1
                )
                st.session_state.final_numbered = response.choices[0].message.content
                st.session_state.step = 3
                st.rerun()
        except Exception as e:
            st.error(f"重编失败：{e}")

# ==========================================
# 阶段 3：最终产出
# ==========================================
elif st.session_state.step == 3:
    st.subheader("🎬 最终分镜定稿")
    st.text_area("Final Result", st.session_state.final_numbered, height=500)
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 下载 TXT", st.session_state.final_numbered, file_name="定稿分镜.txt", use_container_width=True)
    with c2:
        if st.button("⬅️ 返回修改", use_container_width=True):
            st.session_state.step = 2
            st.rerun()

st.divider()
st.caption("2025 AI文案分镜工具 | 紧凑型编辑器架构")
