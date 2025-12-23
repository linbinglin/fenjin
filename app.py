import streamlit as st
from openai import OpenAI
import io
import re

# --- 页面配置 ---
st.set_page_config(page_title="高级分镜重构系统-稳定版", layout="wide")

# --- 初始化 Session State (关键修复) ---
if 'final_result' not in st.session_state:
    st.session_state.final_result = None
if 'draft_result' not in st.session_state:
    st.session_state.draft_result = None

st.title("🎬 电影解说·高级分镜重构系统 (V4.0 稳定版)")
st.markdown("采用 SessionState 技术，防止 API 调用过程中数据丢失或页面重置。")

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 配置面板")
    api_key = st.text_input("请输入 API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") 
    st.divider()
    if st.button("🔄 重置所有内容"):
        st.session_state.final_result = None
        st.session_state.draft_result = None
        st.rerun()

def clean_text(text):
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r'\s+', '', text)
    return text

# --- Prompts ---
PROMPT_STEP1 = "你是一个电影导演。请阅读以下文字流，并根据“视觉画面感”进行初步分镜。要求：1. 画面感切分，每当有新动作、新观察点、新对话时设定为新分镜。2. 动作连贯的请合并。3. 一字不漏，不改顺序。"

PROMPT_STEP2 = """你是一个资深电影剪辑师。请对初稿分镜进行【视觉节奏平衡】处理。
目标：分镜文字量控制在 15-40 字之间（最佳 25-35 字）。
策略：
1. 合并碎镜：少于12字且动作连贯的必须合并。
2. 拆分重镜：超过45字的寻找逻辑点（逗号、连词）精准拆分。
3. 严禁改动原文任何一个字！
格式：1.内容 2.内容"""

# --- 主界面 ---
uploaded_file = st.file_uploader("1. 上传文案 (.txt)", type=['txt'])

# 文本预览区
input_text = ""
if uploaded_file is not None:
    input_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    flat_text = clean_text(input_text)
    
    col_pre1, col_pre2 = st.columns(2)
    with col_pre1:
        with st.expander("查看清洗后的待处理文本"):
            st.write(flat_text)

# --- 执行区 ---
if st.button("🚀 开始双重重构分镜", type="primary"):
    if not api_key:
        st.error("❌ 请先输入 API Key")
    elif not input_text:
        st.error("❌ 请先上传文案")
    else:
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # 步骤一
            with st.status("正在执行：第一阶段 - 画面感知拆解...", expanded=True) as status:
                st.write("发送请求到模型...")
                res1 = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": PROMPT_STEP1},
                        {"role": "user", "content": f"文字流：{flat_text}"}
                    ],
                    temperature=0.3,
                )
                st.session_state.draft_result = res1.choices[0].message.content
                st.write("第一阶段完成。")

                # 步骤二
                st.write("正在执行：第二阶段 - 节奏对齐平衡...")
                res2 = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": PROMPT_STEP2},
                        {"role": "user", "content": f"初稿：{st.session_state.draft_result}"}
                    ],
                    temperature=0.1,
                )
                st.session_state.final_result = res2.choices[0].message.content
                status.update(label="✅ 处理全部完成！", state="complete", expanded=False)
                
        except Exception as e:
            st.error(f"⚠️ 发生错误：{str(e)}")

# --- 结果展示区 (独立于按钮点击，只要 session_state 有值就显示) ---
if st.session_state.final_result:
    st.divider()
    res_col1, res_col2 = st.columns([2, 1])
    
    with res_col1:
        st.subheader("🎬 最终精修分镜稿")
        
        # 实时字数检测显示
        display_lines = []
        for line in st.session_state.final_result.split('\n'):
            if not line.strip(): continue
            content = re.sub(r'^\d+\.', '', line)
            length = len(content)
            if length > 45:
                display_lines.append(f"🔴 [过重:{length}字] {line}")
            elif length < 10:
                display_lines.append(f"🟡 [过碎:{length}字] {line}")
            else:
                display_lines.append(line)
        
        st.text_area("Final Output", "\n".join(display_lines), height=600)
    
    with res_col2:
        st.subheader("🛠️ 操作")
        st.download_button(
            "📥 下载最终分镜 TXT", 
            st.session_state.final_result, 
            file_name="AI平衡分镜.txt",
            use_container_width=True
        )
        if st.checkbox("查看第一遍初稿内容"):
            st.text_area("Step 1 Draft", st.session_state.draft_result, height=300)

st.divider()
st.caption("技术说明：如果程序运行中页面白屏，通常是 API 响应超时。本工具已开启 SessionState 保护，一旦运行成功，结果将持久化显示。")
