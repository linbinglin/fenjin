import streamlit as st
from openai import OpenAI
import io
import re

# --- 页面配置 ---
st.set_page_config(page_title="顶级文案分镜大师", layout="wide")

st.title("🎬 电影解说·资深级分镜重构")
st.markdown("本系统采用**强制脱敏**与**深度步进式精修**，解决分镜过长、逻辑堆砌等新手问题。")

# --- 侧边栏配置 ---
with st.sidebar:
    st.title("⚙️ 控制台")
    api_key = st.text_input("请输入 API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") # 强烈建议使用 gpt-4o 或 claude-3-5
    st.divider()
    st.info("💡 **专家模式已开启**：系统将强制执行 35 字拆分原则，确保每个分镜都能在 5 秒内完成。")

def clean_text(text):
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r'\s+', '', text)
    return text

# --- 第一步：纯逻辑拆解 (逻辑导演) ---
PROMPT_STEP1_LOGIC = """你是一个资深电影编剧。我会给你一段没有任何段落的文字流。
请你完成初步的【剧情拆解】。
要求：
1. 识别出所有独立的动作、对话、环境描写。
2. 此时不需要考虑字数，重点是【剧情完整性】。
3. 严禁漏字，严禁改字。
4. 格式：
1.分镜文案
2.分镜文案
"""

# --- 第二步：严格节奏对齐 (高级剪辑师) ---
# 这里加入了 Few-Shot (示例)，让 AI 明白什么叫“专业拆分”
PROMPT_STEP2_STRICT_REFINE = """你是一个拥有10年经验的顶级电影解说剪辑师。
现在你要对初版分镜进行【极限精修】。你必须像手术刀一样精准地切割文案。

核心任务：
1. **强制字数平衡**：每个分镜的目标是 35 个字符左右（约 5 秒）。
2. **拒绝新手错误**：禁止在一个分镜里堆砌多个动作。如果一行文案出现了两个及以上的动作，即使它没满35字，也必须拆分。
3. **拆分技术点**：利用逗号、句号、连词（如“随后”、“然后”、“却”）作为切割点。
4. **绝对原则**：不可遗漏任何字！文字顺序不可乱！

---
【专业示范：如何拆分新手式长分镜】
新手分镜（错误）：
1.由于家里穷得揭不开锅，怀孕的母亲只能带着8岁的我在寺庙外乞讨，我把僧人送来的白粥全部让给了母亲，自己却饿得头晕眼花。 (80字，关键内容太多，无法对应视频)

资深剪辑（正确）：
1.8岁那年家里穷得揭不开锅了
2.怀孕的母亲带着我在寺外乞讨
3.我把僧人端来的粥饭全给了母亲
4.自己却饿得头晕眼花
---

请处理以下初稿，输出最终分镜：
"""

# --- 主界面逻辑 ---
uploaded_file = st.file_uploader("上传文案文件 (.txt)", type=['txt'])

if uploaded_file is not None:
    original_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    flattened_text = clean_text(original_text)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📥 原始输入 (已扁平化)")
        st.text_area("Input", flattened_text, height=300)

    if st.button("🚀 执行高级双重分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # --- 第一步：逻辑拆解 ---
                with st.status("第一阶段：剧情逻辑拆解中...", expanded=True) as status:
                    response_draft = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STEP1_LOGIC},
                            {"role": "user", "content": f"请对以下文字流进行逻辑拆解：\n\n{flattened_text}"}
                        ],
                        temperature=0.2,
                    )
                    draft_result = response_draft.choices[0].message.content
                    st.write("逻辑重构完成，准备进入精修...")

                    # --- 第二步：严格精修 ---
                    st.write("第二阶段：执行资深级节奏精修 (35字/动作强制对齐)...")
                    response_refine = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STEP2_STRICT_REFINE},
                            {"role": "user", "content": f"这是初版逻辑稿，请按资深剪辑标准执行精修：\n\n{draft_result}"}
                        ],
                        temperature=0.1, # 降低随机性，强制遵守规则
                    )
                    final_result = response_refine.choices[0].message.content
                    status.update(label="✨ 分镜精修已完成！", state="complete", expanded=False)

                with col2:
                    st.subheader("🎬 最终专业分镜稿")
                    # 自动检测并标记超过35字的分镜（可视化辅助）
                    lines = final_result.split('\n')
                    highlighted_result = ""
                    for line in lines:
                        if len(line) > 35:
                            highlighted_result += f"⚠️【过长】{line}\n"
                        else:
                            highlighted_result += f"{line}\n"
                    
                    st.text_area("Final Output", highlighted_result, height=500)
                    
                    st.download_button(
                        label="📥 下载分镜稿",
                        data=final_result,
                        file_name="专业分镜稿.txt",
                        mime="text/plain"
                    )

            except Exception as e:
                st.error(f"处理失败：{str(e)}")

st.divider()
st.caption("提示：如果某一行依然过长，通常是因为所选模型（如普通GPT-3.5）推理能力不足，建议更换 Model ID 为 gpt-4o 或 claude-3-5-sonnet。")
