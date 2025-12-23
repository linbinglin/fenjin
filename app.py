import streamlit as st
from openai import OpenAI
import re

# 页面配置
st.set_page_config(page_title="精准分镜精剪工具", page_icon="✂️", layout="wide")

st.title("✂️ 电影解说：逻辑导演 + 精准精剪")
st.markdown("""
**核心改进：**
1. **第一遍（导演模式）**：负责 85% 的核心逻辑拆解。
2. **第二遍（精剪模式）**：**禁止大规模重写**。采用“若非故障，切勿修理”原则。仅对字数超标或过碎的段落进行外科手术式修正。
""")

# --- 侧边栏配置 ---
st.sidebar.header("⚙️ 模型配置")
api_key = st.sidebar.text_input("请输入 API Key", type="password")
base_url = st.sidebar.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")

model_options = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet-20240620", "gemini-1.5-pro"]
selected_model = st.sidebar.selectbox("选择 Model ID", model_options + ["手动输入"])
model_id = st.sidebar.text_input("自定义 Model ID", value="deepseek-chat") if selected_model == "手动输入" else selected_model

# --- 核心 Prompt 深度重构 ---

# 第一阶段：逻辑导演（负责 85% 的正确率）
PROMPT_STAGE_1 = """你是一个专业的电影导演。
任务：请对以下脱敏文本进行分镜。
分镜标准：根据场景切换、角色更换、动作转折。
硬性要求：
1. 严禁改动、增加或删除原文中的任何一个字。
2. 每个分镜必须反映一个独立的画面逻辑。
格式：数字序号.内容
"""

# 第二阶段：精剪校准员（负责剩下的 15% 修正）
PROMPT_STAGE_2 = """你是一个极其克制的电影脚本【精剪校准员】。
第一遍分镜已经完成了 85% 的工作，你的任务是进行微调，**绝对禁止推翻重来**。

**你的操作守则（优先级排序）：**

1. **观察守则（核心）**：
   - 如果一个分镜的长度在 12 到 35 个汉字之间，且逻辑通顺，请【原封不动】地保留它。
   - 禁止为了修改而修改。

2. **长镜切分（仅针对字数 > 35 的分镜）**：
   - 检查分镜，只有字数超过 35 字（语音超过 5 秒）时，才在最近的语义转折点（如标点、连词、动作起止点）拆分为两个。
   - 拆分后要确保两段话依然是完整的。

3. **碎镜合并（仅针对字数 < 10 的分镜）**：
   - 如果连续两个分镜极短（例如都在 8 字以内），且同属一个动作或场景，请将它们合并。

4. **全文审计**：
   - 对比【原始全文】，确保第一遍分镜中没有漏掉任何文字。如果有漏字，请将其塞回对应的分镜。

**输出要求：**
- 保持第一遍的整体结构不变，仅输出修正后的最终分镜列表（序号.内容）。
"""

# --- 主界面 ---
uploaded_file = st.file_uploader("上传 TXT 文案", type=['txt'])

if uploaded_file is not None:
    # 彻底抹除格式
    raw_content = uploaded_file.getvalue().decode("utf-8")
    cleaned_content = "".join(raw_content.split())
    
    col_in, col_s1, col_s2 = st.columns([1, 1, 1.2])
    
    with col_in:
        st.subheader("1. 抹除格式原文")
        st.text_area("Input", cleaned_content, height=400)

    if st.button("🚀 执行精修分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            try:
                # --- 第一阶段 ---
                with st.status("阶段一：逻辑导演拆解...") as status:
                    res1 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STAGE_1},
                            {"role": "user", "content": cleaned_content}
                        ],
                        temperature=0.3
                    )
                    stage1_out = res1.choices[0].message.content
                    with col_s1:
                        st.subheader("2. 导演初剪版")
                        st.text_area("Stage 1", stage1_out, height=400)
                    
                    # --- 第二阶段 ---
                    status.update(label="阶段二：执行 15% 偏差微调...")
                    res2 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STAGE_2},
                            {"role": "user", "content": f"【原始全文】：\n{cleaned_content}\n\n【初剪版分镜】：\n{stage1_out}"}
                        ],
                        temperature=0.1 # 极低温度，防止 AI 瞎改
                    )
                    final_out = res2.choices[0].message.content
                    status.update(label="精修完成！", state="complete")
                    
                with col_s2:
                    st.subheader("3. 最终精剪对齐版")
                    st.text_area("Final Output", final_out, height=400)
                    st.download_button("下载结果", final_out, file_name="final_storyboard.txt")
                    
            except Exception as e:
                st.error(f"处理失败: {str(e)}")

# --- 逻辑说明 ---
st.markdown("---")
st.info("""
**为什么这样能解决问题？**
- **禁止过度干预**：明确告诉 AI“第一遍已经完成了 85%”，这在心理学上给 AI 设置了一个“锚点”，它会倾向于尊重第一遍的结果。
- **条件触发制**：只有当【字数 > 35】或【字数 < 10】这两个硬指标触发时，AI 才被允许动刀。
- **低温策略**：温度 0.1 确保 AI 走最稳健的路线，不产生幻觉和多余的联想。
""")
