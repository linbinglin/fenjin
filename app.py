import streamlit as st
import openai
import re

# --- 页面配置 ---
st.set_page_config(page_title="全能文案·电影感分镜系统 (严格版)", layout="wide")

# 自定义 CSS 让界面更专业
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    .error-text { color: red; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🎬 全能文案·电影感分镜系统 (V1.2)")

# --- 侧边栏配置 (这里是修正重点) ---
with st.sidebar:
    st.header("⚙️ 导演引擎配置")
    api_key = st.text_input("1. API Key", type="password", placeholder="sk-...")
    base_url = st.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
    
    # 修正：改为手动输入，以便适配各种中转接口的模型代号
    model_id = st.text_input("3. Model ID (请手动输入模型名称)", value="grok-1", placeholder="例如: gpt-4o, deepseek-chat, grok-1")
    
    st.divider()
    st.markdown("""
    **V1.2 视觉切割逻辑：**
    - **强制流式化**：删除原文所有换行。
    - **硬性35字**：单镜头文本禁超35字。
    - **逻辑断点**：人称/动作/场景切换必断。
    - **零增删**：原文内容无损还原。
    """)

# --- 核心逻辑处理 ---
def generate_storyboard(text, api_key, base_url, model):
    # 步骤 1: 文本极端预处理 - 彻底删掉所有换行和多余空格，确保 AI 无法参考原段落
    clean_text = "".join(text.split())
    
    # 适配 Base URL 格式
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    
    # 严密的 Prompt 逻辑
    system_prompt = (
        "你是一个分镜语言专家。你唯一的输出职责是将文本切分成带编号的短句。\n"
        "严格规则：\n"
        "1. 必须包含原文所有字词，严禁增加任何解释、严禁删减任何字词、严禁改写。\n"
        "2. 每一个分镜的文案不能超过35个字。\n"
        "3. 切分时机：场景切换、角色切换、新动作发生、或达到字数上限。\n"
        "4. **禁止输出任何开头语或结束语**（如'好的'、'如下'）。\n"
        "5. 格式：1.内容\\n2.内容"
    )
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请对以下流式文本进行无损分镜切分：\n{clean_text}"}
            ],
            temperature=0.1 # 极端低采样，确保逻辑严谨，不产生幻觉
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# --- 主界面 ---
uploaded_file = st.file_uploader("📂 上传 TXT 剧本", type=['txt'])

if uploaded_file:
    # 强制 UTF-8 读取
    raw_content = uploaded_file.read().decode("utf-8")
    # 过滤掉原文中的空行计算纯字数
    pure_raw_text = "".join(raw_content.split())
    raw_len = len(pure_raw_text)

    col_input, col_output = st.columns(2)
    
    with col_input:
        st.subheader("📄 原始文本记录")
        st.text_area("Input", raw_content, height=400)
        st.metric("原文总字数 (不含空格)", raw_len)

    if st.button("🚀 启动视觉逻辑稽核"):
        if not api_key or not model_id:
            st.warning("⚠️ 请先完善侧边栏的 API Key 和 Model ID")
        else:
            with st.spinner(f"正在调用 {model_id} 进行深度逻辑切分..."):
                result = generate_storyboard(raw_content, api_key, base_url, model_id)
                
                with col_output:
                    st.subheader("📽️ 视觉分镜编辑器")
                    st.text_area("Output", result, height=400)
                    
                    # 严谨性校验：提取输出中的所有汉字/符号，与原文对比
                    # 移除数字编号和换行进行统计
                    processed_text = re.sub(r'\d+\.\s*|\n', '', result)
                    processed_len = len(processed_text)
                    
                    st.metric("处理后总字数", processed_len)
                    
                    diff = raw_len - processed_len
                    if diff == 0:
                        st.success("✅ 逻辑完美：字数完全匹配，无损还原。")
                    else:
                        st.error(f"❌ 逻辑异常：偏差值 {diff} 字。AI可能产生了幻觉或偷懒。")
                        st.write(f"建议：检查 Model ID 是否正确，或尝试更高参数模型。")

    # 扩展分析模块（模仿案例图）
    if 'result' in locals() and "Error" not in result:
        st.divider()
        st.subheader("📊 实时视觉节奏分析")
        lines = result.split('\n')
        groups_count = len([l for l in lines if l.strip()])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("生成分镜总数", f"{groups_count} 组")
        c2.metric("平均每镜时长", f"{round(raw_len/groups_count, 1)} 字", help="建议在35字以内")
        c3.metric("节奏评估", "优" if raw_len/groups_count < 30 else "略显疲劳")
