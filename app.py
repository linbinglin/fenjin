import streamlit as st
from openai import OpenAI
import os

# --- 页面基础设置 ---
st.set_page_config(
    page_title="AI智能文案分镜助手",
    page_icon="🎬",
    layout="wide"
)

# --- 侧边栏：API 设置 ---
st.sidebar.header("⚙️ API 设置")

# 1. 适配第三方中转接口地址
# 注意：OpenAI SDK 通常只需要 Base URL 到 /v1 即可，它会自动追加 /chat/completions
# 如果你的第三方地址严格是 https://blog.tuiwen.xyz/v1/chat/completion，
# 可能需要根据实际情况调整，但在 SDK 中通常填写 https://blog.tuiwen.xyz/v1
default_base_url = "https://blog.tuiwen.xyz/v1"
base_url = st.sidebar.text_input(
    "API Base URL (中转地址)", 
    value=default_base_url,
    help="通常填写到 /v1 即可，例如：https://blog.tuiwen.xyz/v1"
)

api_key = st.sidebar.text_input("API Key", type="password", help="请输入你的 API 密钥")

# 2. 模型选择 (支持自定义输入)
model_options = [
    "gpt-4o",
    "deepseek-chat",
    "claude-3-5-sonnet-20240620",
    "gemini-pro",
    "grok-1",
    "doubao-pro-4k"
]
selected_model = st.sidebar.selectbox(
    "选择 AI 模型 (Model ID)", 
    model_options,
    index=0
)
# 允许用户手动输入模型名称（防止列表不全）
custom_model = st.sidebar.text_input("或手动输入模型名称 (如列表无此模型)", value="")
final_model = custom_model if custom_model else selected_model

# --- 主界面 ---
st.title("🎬 AI 视频文案自动分镜工具")
st.markdown("### 上传 TXT 文本，自动按剧情和时长生成分镜脚本")

# 3. 分镜内容从本地选择文件
uploaded_file = st.file_uploader("请上传文案文件 (.txt)", type=['txt'])

# --- 核心提示词构建 (Prompt Engineering) ---
def build_system_prompt():
    return """
    你是一个优秀的电影解说工作员和专业的分镜师。
    任务：接收用户输入的文本，根据严格的逻辑将其拆解为视频分镜列表。

    【核心原则 - 必须严格遵守】
    1. **绝对忠实原文**：整理后的内容不可遗漏原文中的任何一句话、一个字，严禁修改原文，严禁添加原文以外的任何内容。
    2. **分镜逻辑**：
       - 当角色对话切换、场景切换、动作画面改变时，必须另起一行作为新分镜。
       - 必须根据剧情来划分，保证连贯流畅。
    3. **时长与字数限制 (至关重要)**：
       - 视频配套音频每个分镜只能停留约5秒。
       - **限制**：每一行分镜文案长度必须控制在 **35个字符以内** (包括标点)。
       - 如果原文某一句过长，必须在保持语义通顺的前提下拆分为两个或多个分镜，确保每个分镜对应的音频不会长于视频画面。
    4. **输出格式**：
       - 纯文本输出，每行一个分镜。
       - 必须使用数字序号开头 (1. 2. 3. ...)。

    【输出示例】
    原文：8岁那年家里穷得揭不开锅了怀孕的母亲带着我在寺外乞讨我把僧人端来的粥饭全给了母亲
    输出：
    1.8岁那年家里穷得揭不开锅了
    2.怀孕的母亲带着我在寺外乞讨
    3.我把僧人端来的粥饭全给了母亲

    请立即开始处理，只输出分镜结果，不要包含任何开场白或解释。
    """

# --- 处理逻辑 ---
if uploaded_file is not None:
    # 读取文件内容
    file_content = uploaded_file.read().decode("utf-8")
    
    # 显示原始内容预览
    with st.expander("查看原始文案"):
        st.text_area("原始内容", file_content, height=150)

    # 按钮触发
    if st.button("开始生成分镜", type="primary"):
        if not api_key:
            st.error("❌ 请先在侧边栏输入 API Key")
        else:
            try:
                # 初始化 OpenAI 客户端
                client = OpenAI(
                    api_key=api_key,
                    base_url=base_url
                )

                st.info(f"正在使用模型: {final_model} 进行分析...")
                
                # 创建占位符用于流式输出
                result_placeholder = st.empty()
                full_response = ""

                # 调用 API
                stream = client.chat.completions.create(
                    model=final_model,
                    messages=[
                        {"role": "system", "content": build_system_prompt()},
                        {"role": "user", "content": f"请对以下文本进行分镜处理：\n\n{file_content}"}
                    ],
                    stream=True,
                    temperature=0.7 # 稍微降低创造性，保证忠实原文
                )

                # 流式接收并显示
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        result_placeholder.markdown(full_response)

                st.success("✅ 分镜生成完成！")
                
                # 提供下载按钮
                st.download_button(
                    label="📥 下载分镜脚本 (.txt)",
                    data=full_response,
                    file_name="storyboard_output.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"❌ 发生错误: {str(e)}")
                st.markdown("请检查 API Key、Base URL 是否正确，或模型名称是否有效。")

# --- 使用说明 ---
with st.sidebar:
    st.divider()
    st.markdown("""
    ### 📝 使用指南
    1. 在上方填入 API Key。
    2. 确认 Base URL (默认已适配 tuiwen.xyz)。
    3. 选择或输入你想使用的 AI 模型。
    4. 上传 txt 文件，点击生成。
    
    **关于 35 字符限制：**
    AI 会尽量将每行控制在 35 字以内以适配 5 秒视频时长。
    """)