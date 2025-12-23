import streamlit as st
from openai import OpenAI
import re

# 页面配置
st.set_page_config(page_title="电影解说精细化分镜工具", page_icon="🎬", layout="wide")

st.title("🎬 电影解说文案精细化分镜")
st.markdown("本版本强化了第二遍的**‘强制拆分逻辑’**，确保长文案被精确切分为 5 秒内可消化的分镜。")

# --- 侧边栏配置 ---
st.sidebar.header("⚙️ API 与模型设置")
api_key = st.sidebar.text_input("请输入 API Key", type="password")
base_url = st.sidebar.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")

model_options = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet-20240620", "gemini-1.5-pro", "doubao-pro-128k"]
selected_model = st.sidebar.selectbox("选择或输入模型名称 (Model ID)", model_options + ["手动输入"])
if selected_model == "手动输入":
    model_id = st.sidebar.text_input("请输入自定义 Model ID")
else:
    model_id = selected_model

# --- 核心 Prompt 深度优化 ---

# 第一阶段：宏观剧情拆解（粗剪）
PROMPT_STAGE_1 = """你是一个电影分镜导演。
我会给你一段没有任何换行符的文案。请基于【场景变换、人物对话、重大动作】进行第一次逻辑分镜。
要求：
1. 识别故事的转场和情节转折点。
2. 严禁改动原文任何字词。
3. 此时不需要过度考虑字数，重点是保证剧情逻辑的完整性。
格式：序号.内容
"""

# 第二阶段：微观节奏精修（精剪） - 这是核心改动
PROMPT_STAGE_2 = """你是一个分秒必争的电影剪辑精修师。
你的任务是拿着第一步生成的“粗剪分镜”，进行【微观二次拆解】。

操作准则：
1. **强制扫描长度**：盯着每一个分镜。如果该分镜的字数超过 30 个汉字，说明一个画面放不下，你必须将其拆分为 2 个或多个连续分镜。
2. **寻找微小停顿点**：拆分长分镜时，请寻找逻辑上的微小间隙，例如：
   - 标点符号处（逗号、分号）。
   - 关联词处（“然后”、“接着”、“但是”）。
   - 动作的起承转合（例如：“他跑进屋子/反手锁上了门”）。
3. **连贯性要求**：拆分后的内容必须像电影画面一样丝滑切换。
4. **严禁丢失字词**：你只是在做“切分”手术，不准修改、不准删除、不准增加任何一个字。
5. **拒绝懒惰**：不要原样输出第一步的结果。你的价值就在于把长句切成短镜头，使其完美适配 5 秒一个镜头的节奏。

输出：最终优化后的完整分镜列表，仅保留“序号.内容”格式。
"""

# --- 主界面逻辑 ---
uploaded_file = st.file_uploader("上传 TXT 文案", type=['txt'])

if uploaded_file is not None:
    # 彻底抹除原段落
    raw_content = uploaded_file.getvalue().decode("utf-8")
    cleaned_content = "".join(raw_content.split()) # 强力去除所有空白字符
    
    col_input, col_s1, col_s2 = st.columns([1, 1, 1])
    
    with col_input:
        st.subheader("1. 抹除格式的原文")
        st.text_area("Input", cleaned_content, height=400)

    if st.button("🚀 执行双重精细分镜"):
        if not api_key:
            st.error("请输入 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            try:
                # --- 第一阶段 ---
                with st.spinner("阶段 1：剧情粗剪中..."):
                    res1 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STAGE_1},
                            {"role": "user", "content": cleaned_content}
                        ],
                        temperature=0.3
                    )
                    stage1_result = res1.choices[0].message.content
                
                with col_s1:
                    st.subheader("2. 剧情初次分镜")
                    st.text_area("Stage 1", stage1_result, height=400)
                
                # --- 第二阶段 ---
                with st.spinner("阶段 2：字数精剪与强制拆分..."):
                    res2 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STAGE_2},
                            {"role": "user", "content": f"初次分镜如下，请执行强制精修：\n\n{stage1_result}"}
                        ],
                        temperature=0.1 # 调低温度，让它极其严格地执行拆分
                    )
                    final_result = res2.choices[0].message.content
                
                with col_s2:
                    st.subheader("3. 最终对齐分镜")
                    st.text_area("Final Output", final_result, height=400)
                    st.download_button("下载结果", final_result, file_name="final_storyboard.txt")
                    
            except Exception as e:
                st.error(f"处理失败: {str(e)}")

# --- 说明 ---
st.markdown("---")
st.info("**为什么这次会有效？**\n\n我们将第二遍的任务从‘校对’改成了‘切分’。AI 现在被告知：如果你不拆分超过30个字的分镜，你就是失职的。这种强度的指令能迫使它去分析长句内部的结构。")
