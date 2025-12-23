import streamlit as st
from openai import OpenAI
import io

# --- 页面配置 ---
st.set_page_config(page_title="AI双重分镜大师", layout="wide")

st.title("🎬 电影解说双重分镜精修工具")
st.markdown("采用 **[逻辑初分 + 节奏精修]** 双引擎模式，生成更符合剪辑逻辑的分镜稿。")

# --- 侧边栏配置 ---
with st.sidebar:
    st.title("⚙️ 配置中心")
    api_key = st.text_input("请输入 API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.divider()
    st.info("""
    **双重分镜逻辑：**
    1. **初分：** 识别场景、动作、对话。
    2. **精修：** 优化节奏，合并碎片，拆分冗长段落。
    """)

# --- Prompt 定义 ---

# 第一步：逻辑初分
PROMPT_STEP1_DRAFT = """你是一个专业的电影剪辑师。请对以下文本进行初步分镜。
要求：
1. 识别场景切换、人物对话改变、重大动作改变，并以此作为分镜切口。
2. 保持原文完整，不增不减。
3. 每个分镜逻辑清晰，连贯。
4. 格式：
1.分镜内容
2.分镜内容
"""

# 第二步：精修优化
PROMPT_STEP2_REFINE = """你是一个资深的视频分镜导演。现在请你对下方的初稿分镜进行“节奏精修”。
你的目标是让分镜文案的阅读时长更适合视频剪辑（每个分镜建议在3-6秒之间）。

精修准则：
1. **合并碎片**：如果连续几个分镜字数过少（如2-5个字）且属于同一场景动作，请将其合并，避免视觉疲劳。
2. **拆分冗长**：如果单个分镜文字过多（建议超过40字为上限参考），请在不改变原文文字的前提下，寻找自然的语感停顿处拆分为两个分镜。
3. **保持平衡**：不需要强求每行字数完全一致，重点是“剧情逻辑自洽”和“节奏舒适”。
4. **绝对原则**：严禁修改、增加或删除原文中的任何一个字。必须严格遵守原文顺序。
5. **格式输出**：只输出最终的分镜列表，以数字编号开头。
"""

# --- 主界面逻辑 ---
uploaded_file = st.file_uploader("选择本地 TXT 文案文件", type=['txt'])

if uploaded_file is not None:
    raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 原始文本")
        st.text_area("Original", raw_text, height=400)

    if st.button("🚀 开始双重深度分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # --- 第一步：初分 ---
                with st.status("正在进行第一遍：剧情逻辑分析...", expanded=True) as status:
                    response_draft = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STEP1_DRAFT},
                            {"role": "user", "content": raw_text}
                        ],
                        temperature=0.3,
                    )
                    draft_result = response_draft.choices[0].message.content
                    st.write("初稿生成完毕...")

                    # --- 第二步：精修 ---
                    st.write("正在进行第二遍：节奏精修与节奏对齐...")
                    response_refine = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STEP2_REFINE},
                            {"role": "user", "content": f"这是分镜初稿，请进行精修处理：\n\n{draft_result}"}
                        ],
                        temperature=0.2,
                    )
                    final_result = response_refine.choices[0].message.content
                    status.update(label="分镜精修完成！", state="complete", expanded=False)

                with col2:
                    st.subheader("🎬 最终精修分镜")
                    st.text_area("Final Output", final_result, height=400)
                    
                    st.download_button(
                        label="📥 下载最终分镜稿",
                        data=final_result,
                        file_name="双重精修分镜.txt",
                        mime="text/plain"
                    )

            except Exception as e:
                st.error(f"处理失败：{str(e)}")

# --- 使用技巧 ---
st.divider()
with st.expander("💡 为什么采用双重分镜？"):
    st.write("""
    - **逻辑感**：第一遍让AI像导演一样理解故事，不会因为字数限制而切断一个完整的动作。
    - **节奏感**：第二遍让AI像剪辑师一样控制时长。它会发现第一遍中“太长的句子”并手动切开，或者把“太碎的动作”合并。
    - **稳定性**：通过两轮对话，AI对原文的记忆会加深，有效降低遗漏文字的概率。
    """)
