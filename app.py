import streamlit as st
from openai import OpenAI
import re

# --- 页面配置 ---
st.set_page_config(
    page_title="AI 导演级剧情分镜 (逻辑优先版)",
    page_icon="🎬",
    layout="wide"
)

# --- 侧边栏：设置 ---
st.sidebar.header("⚙️ 导演控制台")

# 1. API 设置
default_base_url = "https://blog.tuiwen.xyz/v1"
base_url = st.sidebar.text_input("API Base URL", value=default_base_url)
api_key = st.sidebar.text_input("API Key", type="password")

# 2. 模型选择 (自由度最高)
st.sidebar.subheader("🤖 模型选择")
model_options = ["gpt-4o", "deepseek-chat", "claude-3-5-sonnet-20240620", "gemini-pro"]
selected_list_model = st.sidebar.selectbox("常用模型", model_options, index=0)
custom_model_input = st.sidebar.text_input("或手动输入模型 ID", value="", help="优先使用手动输入的ID")
final_model = custom_model_input if custom_model_input.strip() else selected_list_model

# --- 核心逻辑函数 ---

def clean_text_structure(text):
    """
    清洗函数：将原文“揉”成一团，强迫 AI 重新梳理。
    """
    # 移除换行、制表符
    text = text.replace('\n', '').replace('\r', '').replace('\t', '')
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_director_prompt():
    return """
    你是一位经验丰富的**电影分镜导演**。你的任务是根据剧情的**视觉逻辑**对文本进行分镜拆分。

    ### 核心原则 (Logic First)
    **请完全忽略原本的段落结构，也不要被字数严格限制。**
    你需要根据**“画面是否需要切换”**来决定是否换行。

    ### 什么时候应该分镜（切分标准）？
    1.  **角色切换**：对话权从 A 转移到 B（如：A说完话，轮到B说 -> 切）。
    2.  **场景/空间转换**：从室内转到室外，或时间跨度变化（如：回忆结束回到现实 -> 切）。
    3.  **视觉焦点/动作突变**：
        -   前半句是静态描写（看着窗外），后半句突然发生动作（杯子摔碎了） -> 切。
        -   原本是全景叙述，突然转为特写心理活动 -> 切。

    ### 什么时候【不】应该分镜？
    1.  **连贯的叙述**：如果一句话很长（例如50-60字），但它描述的是**同一个连续的动作**或**同一个人的完整心理独白**，**请保留在同一行，不要打断情绪**。
    2.  **不要破碎化**：禁止为了凑“短句”而把一句完整的话强行拆成两半（例如：“8岁那年家里穷得”和“揭不开锅了”必须在同一行）。

    ### 输出要求
    1.  **绝对忠实**：不得删减、修改、增加原文任何字词。
    2.  **格式**：仅输出带数字序号的分镜列表 (1. 2. 3...)。
    """

# --- 主界面 ---
st.title("🎬 剧情自动分镜工具 (逻辑优先版)")
st.markdown("""
> **设计理念更新**：
> 不再强制 35 字切分。AI 将模拟导演思维，仅在**角色切换、场景转换、动作突变**时进行分镜，确保故事的连贯性和画面的合理性。
""")

uploaded_file = st.file_uploader("上传剧本/文案 (.txt)", type=['txt'])

if uploaded_file:
    # 1. 读取并清洗
    raw_content = uploaded_file.read().decode("utf-8")
    merged_content = clean_text_structure(raw_content)

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1️⃣ 剧情流 (已清洗)")
        st.info("已去除原文段落，构建连续剧情流：")
        st.text_area("Source Stream", merged_content, height=500, disabled=True)

    with col2:
        st.subheader("2️⃣ 导演分镜表")
        result_placeholder = st.empty()
        
        start_btn = st.button("开始导演分镜", type="primary", use_container_width=True)

        if start_btn:
            if not api_key:
                st.error("⚠️ 请输入 API Key")
            else:
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    
                    st.toast(f"正在调用 {final_model} 进行逻辑分析...")
                    
                    stream = client.chat.completions.create(
                        model=final_model,
                        messages=[
                            {"role": "system", "content": get_director_prompt()},
                            {"role": "user", "content": f"请对以下剧情流进行分镜：\n\n{merged_content}"}
                        ],
                        stream=True,
                        temperature=0.2 # 稍微提高一点点温度，让它理解语义逻辑，但依然保持克制
                    )

                    full_response = ""
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            result_placeholder.text_area("生成结果...", full_response, height=500)
                    
                    # 最终展示
                    result_placeholder.text_area("最终分镜表", full_response, height=500)
                    st.success("✅ 分镜完成！")
                    
                    st.download_button(
                        label="📥 下载分镜脚本",
                        data=full_response,
                        file_name="director_storyboard.txt",
                        mime="text/plain"
                    )

                except Exception as e:
                    st.error(f"❌ 错误: {e}")
