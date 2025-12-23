import streamlit as st
from openai import OpenAI

# --- 页面基础设置 ---
st.set_page_config(
    page_title="文案分镜标准化工具",
    page_icon="🎬",
    layout="wide"
)

# --- 侧边栏：配置中心 ---
st.sidebar.header("⚙️ 核心配置")

# 1. API 地址配置
default_base_url = "https://blog.tuiwen.xyz/v1"
base_url = st.sidebar.text_input(
    "中转接口地址 (Base URL)", 
    value=default_base_url,
    help="请输入第三方接口地址，通常以 /v1 结尾"
)

api_key = st.sidebar.text_input("API Key", type="password", help="请输入你的 API 密钥")

# 2. 模型选择 (修复了你提到的选项缺失问题)
st.sidebar.subheader("🤖 模型选择")
model_list = [
    "gpt-4o",
    "deepseek-chat", 
    "claude-3-5-sonnet-20240620",
    "gemini-pro",
    "doubao-pro-4k",
    "grok-1"
]
selected_model = st.sidebar.selectbox("选择预设模型", model_list, index=0)
custom_model_id = st.sidebar.text_input("或输入自定义模型 ID (优先使用)", placeholder="例如：gpt-4-turbo")

# 确定最终使用的模型ID
final_model = custom_model_id if custom_model_id.strip() else selected_model

# --- 系统提示词 (Prompt Engineering) ---
# 这是最关键的部分，让AI学习你提供的合格文本格式
def get_system_prompt():
    return """
    你是一个专业的电影解说文案分镜师。你的工作是将用户上传的小说或长文案，进行精准的【分镜拆解】。

    ### 任务目标
    将连贯的文本拆解为带有序号的分镜列表。整理后的内容**不可遗漏原文中的任何一句话、一个字**，不能改变原文故事结构，**禁止添加原文以外任何内容**。

    ### 分镜逻辑 (严格执行)
    1.  **场景与动作切换**：当角色对话切换、场景转换、动作画面发生改变时，必须另起一行，用新的分镜数字表示。
    2.  **时长控制 (核心)**：
        *   每个分镜对应视频画面约5秒。
        *   **字数限制**：单行文案严格控制在 **35个字符以内**。
        *   如果原文句子过长，必须在语义通顺的地方切开，分成两个或多个分镜序号。
    3.  **格式要求**：
        *   纯文本输出，每行开头必须是数字序号 (1. 2. 3...)。
        *   对话内容如果有引号或【】，请保留。

    ### 学习样本 (请模仿以下风格)
    【输入】：
    我是名满京城的神秘画师一笔一划皆能勾动男子情欲世间女子骂我伤风败俗可男人们却视若珍宝
    【输出】：
    1.我是名满京城的神秘画师
    2.一笔一划皆能勾动男子情欲
    3.世间女子骂我伤风败俗
    4.可男人们却视若珍宝

    【输入】：
    门突然被推开床帷顺势落下，卖力的声音不减所有人的目光却都聚集在了我身上【这画的当真是惟妙惟肖不愧是京城第一春宫画师，要不然你给我们也画上一副？】
    【输出】：
    22.门突然被推开床帷顺势落下，卖力的声音不减
    23.所有人的目光却都聚集在了我身上
    24.【这画的当真是惟妙惟肖不愧是京城第一春宫画师，要不然你给我们也画上一副？】

    现在，请对用户提供的文本进行同样的处理。不要输出任何多余的解释，直接开始标号输出。
    """

# --- 主界面 ---
st.title("🎬 电影解说文案自动分镜系统")
st.markdown(f"当前运行模型：`{final_model}`")

uploaded_file = st.file_uploader("请选择本地 TXT 文案文件", type=['txt'])

if uploaded_file is not None:
    # 读取文件
    file_content = uploaded_file.read().decode("utf-8")
    
    # 左右分栏显示：左边原文，右边结果
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 原始文案")
        st.text_area("原文预览", file_content, height=600)

    with col2:
        st.subheader("🎥 分镜结果")
        # 占位符
        result_placeholder = st.empty()
        
        # 只有点击按钮才开始处理
        generate_btn = st.button("开始拆解分镜", type="primary", use_container_width=True)

        if generate_btn:
            if not api_key:
                st.error("⚠️ 请先在侧边栏填写 API Key")
            else:
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    
                    # 流式请求
                    stream = client.chat.completions.create(
                        model=final_model,
                        messages=[
                            {"role": "system", "content": get_system_prompt()},
                            {"role": "user", "content": file_content}
                        ],
                        stream=True,
                        temperature=0.1 # 温度设低，保证绝对忠实原文，不胡乱发挥
                    )

                    full_response = ""
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            result_placeholder.text_area("生成中...", full_response, height=600)
                    
                    # 最终显示（去掉生成中状态，显示最终结果）
                    result_placeholder.text_area("分镜列表", full_response, height=600)
                    
                    st.success("✅ 分镜拆解完成！")
                    
                    # 下载按钮
                    st.download_button(
                        label="📥 下载分镜文本 (.txt)",
                        data=full_response,
                        file_name="storyboard_output.txt",
                        mime="text/plain"
                    )

                except Exception as e:
                    st.error(f"❌ 处理出错: {e}")
                    st.warning("请检查 API Key 是否正确，或模型 ID 是否支持。")
