import streamlit as st
from openai import OpenAI
import re

# --- 页面基础设置 ---
st.set_page_config(
    page_title="AI深度剧情分镜助手",
    page_icon="🎬",
    layout="wide"
)

# --- 侧边栏：API 与模型设置 ---
st.sidebar.header("⚙️ 设置中心")

# 1. 接口地址
default_base_url = "https://blog.tuiwen.xyz/v1"
base_url = st.sidebar.text_input(
    "API Base URL (中转地址)", 
    value=default_base_url,
    help="请填写你的第三方接口地址"
)

api_key = st.sidebar.text_input("API Key", type="password", help="请输入密钥")

# 2. 模型选择 (修正：增加自定义选项)
st.sidebar.markdown("### 🤖 模型选择")
model_options = [
    "gpt-4o",
    "deepseek-chat",
    "claude-3-5-sonnet-20240620",
    "gemini-pro",
    "doubao-pro-4k"
]
# 下拉菜单选择
selected_list_model = st.sidebar.selectbox("选择预设模型", model_options, index=0)
# 自定义输入框
custom_model_input = st.sidebar.text_input("或手动输入模型 ID (如 gpt-4-turbo)", value="")

# 逻辑：如果有手动输入，优先用手动输入的；否则用下拉菜单的
final_model = custom_model_input if custom_model_input.strip() else selected_list_model

st.sidebar.info(f"当前使用模型 ID: **{final_model}**")

# --- 核心功能函数 ---

def clean_text_structure(text):
    """
    预处理函数：去除所有换行符、多余空格，将文本合并为一行。
    强制 AI 无法参考原文的段落结构，必须重新思考。
    """
    # 去除换行符和制表符
    text = text.replace('\n', '').replace('\r', '').replace('\t', '')
    # 去除连续的空格，只保留一个
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_system_prompt():
    return """
    你是一个专业的影视解说分镜师。你的任务是接收一段**连续的、无格式的纯文本**，根据剧情逻辑和视觉节奏，将其重新拆解为分镜列表。

    ### 核心思考逻辑（Step-by-Step）
    1.  **重构节奏**：忽略原文的任何句式结构，完全根据“画面感”来断句。
    2.  **时长对齐（关键）**：
        -   视频分镜通常为 3-5 秒。
        -   **强制限制**：每个分镜文案长度不得超过 **35个字符**。
        -   如果一句话太长（例如超过35字），必须在语义通顺的标点处切断，分为两个分镜。
    3.  **画面切换判断**：
        -   当出现【新角色说话】时，切分镜。
        -   当【动作发生变化】时，切分镜。
        -   当【场景转换】时，切分镜。

    ### 严格约束
    1.  **完整性**：绝对不可遗漏原文任何一个字，不可修改原文，不可添加原文之外的内容。
    2.  **格式**：每行必须以数字序号开头 (1. 2. 3...)。

    ### 示例
    【输入纯文本】：
    8岁那年家里穷得揭不开锅了怀孕的母亲带着我在寺外乞讨我把僧人端来的粥饭全给了母亲施粥的将军府老妇人让人领我过来问都饿成人干了怎么不吃
    
    【输出分镜】：
    1.8岁那年家里穷得揭不开锅了
    2.怀孕的母亲带着我在寺外乞讨
    3.我把僧人端来的粥饭全给了母亲
    4.施粥的将军府老妇人，让人领我过来问
    5.都饿成人干了怎么不吃

    请直接开始处理，只输出分镜列表。
    """

# --- 主页面 UI ---
st.title("🎬 剧情文案自动分镜工具 (深度重组版)")
st.markdown("""
**逻辑说明：**
1. 系统会自动将上传的文案**去除所有格式和换行**，合并为一整段。
2. 强制 AI 根据剧情内容和 35字/5秒 的规则重新进行切分。
""")

uploaded_file = st.file_uploader("上传文案 (.txt)", type=['txt'])

if uploaded_file:
    # 1. 读取原文
    raw_content = uploaded_file.read().decode("utf-8")
    
    # 2. 预处理：清洗格式，合并文本
    merged_content = clean_text_structure(raw_content)

    # 3. 界面展示对比
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1️⃣ 预处理后的“纯文本”")
        st.caption("已去除原文段落，强制 AI 重新思考节奏：")
        st.text_area("Merged Text", merged_content, height=400, disabled=True)

    with col2:
        st.subheader("2️⃣ AI 分镜结果")
        st.caption(f"模型：{final_model} | 限制：35字/行")
        
        result_placeholder = st.empty()
        start_btn = st.button("开始深度分镜", type="primary", use_container_width=True)

        if start_btn:
            if not api_key:
                st.error("⚠️ 请先配置 API Key")
            else:
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    
                    stream = client.chat.completions.create(
                        model=final_model,
                        messages=[
                            {"role": "system", "content": get_system_prompt()},
                            {"role": "user", "content": merged_content} # 传入合并后的文本
                        ],
                        stream=True,
                        temperature=0.1 # 低温度确保不乱改字
                    )

                    full_response = ""
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            result_placeholder.text_area("Processing...", full_response, height=400)
                    
                    # 最终定格
                    result_placeholder.text_area("Final Output", full_response, height=400)
                    st.success("✅ 分镜生成完毕！")
                    
                    st.download_button(
                        label="📥 下载分镜脚本",
                        data=full_response,
                        file_name="ai_storyboard.txt",
                        mime="text/plain"
                    )

                except Exception as e:
                    st.error(f"❌ 运行出错: {e}")
