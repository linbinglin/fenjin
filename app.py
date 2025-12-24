import streamlit as st
import openai
import re

# --- 页面配置 ---
st.set_page_config(page_title="全能文案·电影感分镜系统 V1.1", layout="wide")

st.title("🎬 全能文案·电影感分镜系统 (V1.1)")
st.caption("针对音画同步、内容重叠深度优化，适配全题材文案。")

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 导演引擎配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.selectbox("Model ID (模型选择)", 
                           ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet-20240620", "grok-1", "doubao-pro-32k"])
    
    st.divider()
    st.markdown("""
    **V1.1 视觉切割准则：**
    1. **主谓镜头**：人称切换必须断开。
    2. **动作即分镜**：一个核心动作完成后必须切镜。
    3. **硬性35字**：单行禁止超过35字（适配5秒音频）。
    """)

# --- 逻辑处理函数 ---
def process_text_to_storyboard(raw_text):
    # 逻辑点7：预处理，删掉原文所有段落/换行，使文本变成流式
    clean_text = re.sub(r'\s+', '', raw_text)
    
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    
    prompt = f"""
    你是一个极其严谨的分镜助理。
    任务：将以下文本拆分为视觉分镜脚本。
    
    严格规则：
    1. 必须保留原文所有字词，严禁添加、删减或改写任何内容。
    2. 拆分触发点：
       - 场景、地点、时间发生变化。
       - 不同的角色开始说话或行动。
       - 原文中描述了一个新的动作。
       - 单段文字长度接近或达到35个字符。
    3. 每一段内容必须精简，确保朗读时间在5秒以内（约35字）。
    4. 输出格式必须是：
       1. 分镜内容A
       2. 分镜内容B
       ...
    
    待处理文本：
    {clean_text}
    """
    
    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "你是一个电影分镜师，只负责按规则拆分文本，严禁废话。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3 # 低随机性确保严谨
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# --- 主界面 ---
uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    content = uploaded_file.read().decode("utf-8")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 原始文本记录")
        st.text_area("Input", content, height=400)
        char_count = len(content)
        st.info(f"原文总字数：{char_count}")

    if st.button("🚀 启动视觉无损分镜"):
        if not api_key:
            st.error("请输入 API Key")
        else:
            with st.spinner("正在进行视觉单元规划..."):
                result = process_text_to_storyboard(content)
                
                with col2:
                    st.subheader("📽️ 视觉分镜编辑器")
                    st.text_area("Output", result, height=400)
                    
                    # 简单审计逻辑
                    res_char_count = len(re.sub(r'\d+\.\s*|\n', '', result))
                    st.success(f"处理后总字数：{res_char_count}")
                    
                    diff = char_count - res_char_count
                    if abs(diff) < 5:
                        st.metric("偏差值", f"{diff} 字", delta="合格", delta_color="normal")
                    else:
                        st.metric("偏差值", f"{diff} 字", delta="不合格/有增删", delta_color="inverse")

# --- 实时视觉节奏分析 (模拟展示) ---
if 'result' in locals():
    st.divider()
    st.subheader("📊 实时视觉节奏分析")
    # 这里未来可以扩展：分析每组分镜的字数分布图，可视化显示哪些镜头过长
