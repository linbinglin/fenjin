import streamlit as st
from openai import OpenAI
import time

# 页面配置
st.set_page_config(page_title="高级文案双重分镜助手", page_icon="🎬", layout="wide")

st.title("🎬 电影解说文案双重分镜工具")
st.markdown("""
本工具采用**双阶段分镜逻辑**：
1. **初次分镜**：深入理解剧情、场景和动作，保持文案连贯。
2. **二次优化**：核对原文完整性，并针对过长的分镜进行平滑拆分，确保音画同步。
""")

# --- 侧边栏配置 ---
st.sidebar.header("⚙️ API 配置")
api_key = st.sidebar.text_input("请输入 API Key", type="password")
base_url = st.sidebar.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.selectbox(
    "选择模型名称 (Model ID)",
    ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet-20240620", "gemini-1.5-pro", "grok-1"]
)

# --- 核心 Prompt 定义 ---

# 第一阶段：剧情逻辑拆解
PROMPT_STAGE_1 = """你是一个专业的电影分镜师。
请对以下文案进行初次分镜处理。
分镜原则：
1. 逻辑优先：严格根据场景切换、角色说话切换、重大动作改变进行分镜。
2. 保持连贯：不要为了字数而生硬切断句子，确保每一段分镜是一段完整的视听语言。
3. 严禁改动：不准增加、删减或修改原文中的任何一个字。
4. 格式：序号.文案内容
"""

# 第二阶段：优化与校对
PROMPT_STAGE_2 = """你是一个经验丰富的电影剪辑审核员。
现有初次分镜后的脚本，请进行二次优化和核对：
1. 检查遗漏：确保初版分镜完整保留了原始文案的所有文字，如有遗漏请补全。
2. 节奏控制：检查每个分镜的长度。如果某个分镜文案明显过长（例如远超 50-60 字），请在不破坏语意的前提下，将其平滑拆分为两个相连的分镜，以便于后期视频对齐。
3. 保持自然：如果文案本身很精简，不要强行拆分，保持叙事节奏。
4. 最终输出：仅输出优化后的分镜结果，格式为“数字.文案内容”，每行一个分镜。
"""

# --- 主界面逻辑 ---
uploaded_file = st.file_uploader("选择本地 TXT 文案文件", type=['txt'])

if uploaded_file is not None:
    original_text = uploaded_file.getvalue().decode("utf-8")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("原文内容")
        st.text_area("Original Text", original_text, height=400)

    if st.button("开始双重分镜处理"):
        if not api_key:
            st.error("请先输入 API Key！")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # --- 第一步：初次分镜 ---
            with st.status("正在进行阶段一：剧情逻辑拆解...") as status:
                try:
                    res1 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STAGE_1},
                            {"role": "user", "content": original_text}
                        ],
                        temperature=0.3
                    )
                    stage1_result = res1.choices[0].message.content
                    st.write("阶段一完成！")
                    
                    # --- 第二步：二次优化 ---
                    st.write("正在进行阶段二：核对遗漏与节奏优化...")
                    res2 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STAGE_2},
                            {"role": "user", "content": f"原始文案：\n{original_text}\n\n初版分镜：\n{stage1_result}"}
                        ],
                        temperature=0.2
                    )
                    final_result = res2.choices[0].message.content
                    status.update(label="处理完成！", state="complete")
                    
                    with col2:
                        st.subheader("最终分镜结果")
                        st.text_area("Final Storyboard", final_result, height=400)
                        
                        st.download_button(
                            label="下载最终分镜脚本",
                            data=final_result,
                            file_name=f"最终分镜_{uploaded_file.name}",
                            mime="text/plain"
                        )
                        
                except Exception as e:
                    st.error(f"处理失败：{str(e)}")

# --- 使用建议 ---
st.markdown("---")
with st.expander("💡 为什么采用两步法？"):
    st.write("""
    - **理解力最大化**：第一步不设限，让 AI 像读小说一样理解故事，分出的镜更符合电影感。
    - **纠错机制**：第二步通过将“原文”和“初版”同时喂给 AI，它能像校对员一样发现哪句话漏掉了。
    - **柔性对齐**：第二步中，AI 会识别出那些“一口气读不完”的长句子并进行逻辑拆分，而不是生硬地每35个字砍一刀。
    """)
