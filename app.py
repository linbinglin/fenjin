import streamlit as st
from openai import OpenAI
import io
import re

# --- 页面配置 ---
st.set_page_config(page_title="专业级AI分镜导演", layout="wide")

st.title("🎬 电影解说·高级分镜重构系统 (V3.0)")
st.markdown("解决分镜过碎或过长的问题，建立真正的**镜头节奏感**。")

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 控制台")
    api_key = st.text_input("请输入 API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") 
    st.divider()
    st.info("💡 **逻辑更新：** 采用‘动态缓冲区’算法，自动合并碎镜，拆分重镜。")

def clean_text(text):
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r'\s+', '', text)
    return text

# --- 第一步：视觉beat拆解 ---
PROMPT_STEP1_VISUAL = """你是一个电影导演。请阅读以下文字流，并根据“视觉画面感”进行初步分镜。
要求：
1. **画面感切分**：每当文字描述了一个新的动作、一个新的观察对象、或者一段新的对话时，设定为一个分镜。
2. **拒绝碎纸机**：不要为了分镜而分镜。如果“他站起身”和“走向门口”是连贯动作，请合并为一行。
3. **保持原文**：一字不漏，不改顺序。
"""

# --- 第二步：高级剪辑平衡 (削峰填谷) ---
PROMPT_STEP2_BALANCE = """你是一个资深的电影剪辑师。现在请你对初稿分镜进行【视觉节奏平衡】处理。
你的目标是确保每个分镜的文字量在 15-40 字之间（最佳为 25-35 字）。

请执行以下【平衡策略】：
1. **合并碎镜（填谷）**：
   - 如果一个分镜字数太少（如少于 12 个字），且与下一个分镜在逻辑/动作上是连贯的，**必须合并**。
   - 示例：将“1.他推开门”“2.走了进去”合并为“1.他推开门走了进去”。

2. **拆分重镜（削峰）**：
   - 如果一个分镜字数过多（超过 45 字），必须在不改变字词的前提下，寻找逗号、连词或逻辑停顿点**精准拆分**。
   - 拆分后的两段必须依然具有独立的画面感。

3. **对话处理**：
   - 每一句不同角色的对话必须独立成镜，但如果对话很短，可以和其动作描述合并。

4. **严格限制**：
   - 严禁增加、删除、修改原文中的任何一个字！
   - 保持分镜编号。

输出格式：
1.文案内容
2.文案内容
"""

# --- 主界面 ---
uploaded_file = st.file_uploader("上传文案 (.txt)", type=['txt'])

if uploaded_file is not None:
    original_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    flattened_text = clean_text(original_text)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📋 待处理文字流")
        st.text_area("Flattened Text", flattened_text, height=300)

    if st.button("🔥 执行专业节奏分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # --- Step 1: 视觉拆解 ---
                with st.status("正在进行阶段一：视觉画面捕捉...", expanded=True) as status:
                    res1 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STEP1_VISUAL},
                            {"role": "user", "content": flattened_text}
                        ],
                        temperature=0.3,
                    )
                    draft = res1.choices[0].message.content
                    st.write("已完成初步画面拆解...")

                    # --- Step 2: 节奏平衡 ---
                    st.write("正在进行阶段二：节奏平衡（消除碎镜与长镜）...")
                    res2 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STEP2_BALANCE},
                            {"role": "user", "content": f"这是分镜初稿，请执行削峰填谷平衡处理：\n\n{draft}"}
                        ],
                        temperature=0.1,
                    )
                    final = res2.choices[0].message.content
                    status.update(label="✅ 分镜平衡重构完成！", state="complete")

                with col2:
                    st.subheader("🎬 节奏平衡分镜稿")
                    
                    # 质量监控可视化
                    processed_lines = []
                    for line in final.split('\n'):
                        if not line.strip(): continue
                        # 简单的字数检测逻辑
                        clean_line = re.sub(r'^\d+\.', '', line)
                        length = len(clean_line)
                        if length > 45:
                            processed_lines.append(f"🔴[过长:{length}字] {line}")
                        elif length < 10:
                            processed_lines.append(f"🟡[过碎:{length}字] {line}")
                        else:
                            processed_lines.append(line)
                    
                    st.text_area("Final Result", "\n".join(processed_lines), height=500)
                    
                    st.download_button("📥 下载分镜稿", final, file_name="平衡分镜.txt")

            except Exception as e:
                st.error(f"处理失败：{str(e)}")

# --- 逻辑解释 ---
st.divider()
with st.expander("🛠️ 为什么这次的分镜会更合理？"):
    st.write("""
    1. **解决了“碎纸机”问题**：在 Step 2 明确要求“填谷”，如果 AI 敢分出只有 5 个字的分镜，会被强制合并。
    2. **解决了“大段落”问题**：通过“削峰”指令，45字以上的段落会被强制寻找呼吸点切割。
    3. **视觉焦点优先**：Step 1 引导 AI 先看“画面”，而不是先数“字数”，这保证了分镜是符合电影逻辑的。
    4. **可视化监控**：结果框中会用 🔴 和 🟡 标记出 AI 依然没处理好的地方，方便你快速微调。
    """)
