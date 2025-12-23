import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 核心辅助函数 ---
def get_pure_text(text):
    """提取纯文本，用于最终字数对账"""
    text = re.sub(r'\d+[\.、]\s*', '', text)
    return "".join(text.split())

# --- 页面配置 ---
st.set_page_config(page_title="解说分镜·黄金平衡版", layout="wide")

st.sidebar.title("🎬 导演工作台 V8")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.success("""
**🎞️ 黄金平衡准则：**
1. **叙事单元**：每个分镜必须是一个完整的动作或画面。
2. **拒绝碎镜**：严禁 15 字以下的“机械换行”。
3. **弹性限长**：目标 30 字，上限可宽限至 38 字以保证语意完整。
4. **0字丢失**：像素级还原原文。
""")

# --- 主界面 ---
st.title("🎞️ 电影解说·黄金平衡分镜系统")
st.caption("解决机械分镜过碎、语意断裂问题，生成具备“电影节奏感”的脚本。")

uploaded_file = st.file_uploader("📂 上传文案 (.txt)", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    # 清洗：合并为有序流
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    # 监控看板
    st.subheader("📊 文案逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 生成黄金平衡分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                with st.spinner('导演正在规划镜头节奏...'):
                    # --- V8 核心指令：不再机械计数，而是视觉叙事 ---
                    system_prompt = """你是一个顶级的电影解说导演，拥有极佳的叙事节奏感。
任务：将文本拆分为“黄金平衡”的分镜脚本。

【黄金平衡原则】：
1. **一个分镜 = 一个视觉动作单元**：每个编号的内容必须包含一个相对完整的叙事动作（谁+做了什么+结果）。
2. **严禁碎片化**：除非是极短的对话切换，否则绝对禁止出现低于 15 个字的分镜。如果一句话很短，必须强行与前后文合并。
3. **弹性长度（核心）**：理想长度为 28-35 字（对应 5 秒解说）。为了保持语意连贯，单行可以放宽到 38 字。不要为了死守 35 字而把一个完整的词或短句切断。
4. **0字损失**：你必须 1:1 还原原文，一个字不能少，顺序不能乱，但要根据节奏重新组合。
5. **万能适配**：适用于任何题材。逻辑是：观察文案中的“动作点”和“呼吸点”，以此作为切分依据。

【执行方式】：
- 读入一段话 -> 感受其画面感 -> 将相关的动作聚合在一起 -> 检查字数（25-38字） -> 编号输出。
- 如果一句话有 50 字，请寻找中间的逻辑转折点拆分为两段，而不是机械对半切。

【输出格式】：
1.内容内容
2.内容内容
(严禁输出描述词、括号、前言)"""

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文本进行无损的、黄金平衡分镜处理，单行约30-35字，严禁碎镜：\n\n{input_stream}"}
                        ],
                        temperature=0, 
                    )

                    result = response.choices[0].message.content
                    output_stream = get_pure_text(result)
                    output_len = len(output_stream)
                    
                    # 分析行
                    lines = [l.strip() for l in result.split('\n') if re.match(r'^\d+', l.strip())]
                    count = len(lines)
                    
                    analysis_data = []
                    for i, line in enumerate(lines):
                        content = re.sub(r'^\d+[\.、]\s*', '', line)
                        ln = len(content)
                        # 黄金平衡状态判定
                        if ln < 15: status = "🟡 偏碎"
                        elif 15 <= ln <= 38: status = "✅ 理想"
                        else: status = "🔴 过长"
                        analysis_data.append({"序号": i+1, "内容预览": content, "字数": ln, "状态": status})
                    df = pd.DataFrame(analysis_data)

                    # 更新看板
                    m2.metric("生成分镜数", f"{count} 组")
                    m3.metric("还原字数", f"{output_len} 字")
                    diff = output_len - input_len
                    m4.metric("偏差", f"{diff} 字")

                    st.divider()

                    # 展示区
                    col_a, col_b = st.columns([1.5, 1])
                    with col_a:
                        st.subheader("📝 分镜预览区")
                        if diff == 0: st.success("🎉 文字 100% 无损还原")
                        else: st.warning(f"⚠️ 偏差：{diff} 字")
                        
                        # 模拟成功案例的视觉样式
                        for _, row in df.iterrows():
                            bg_color = "#f0fff0" if "✅" in row['状态'] else "#fffacd"
                            st.markdown(f"""
                            <div style="background-color:{bg_color}; padding:10px; border-radius:5px; margin-bottom:5px; border-left:5px solid green;">
                            <b>{row['序号']}.</b> {row['内容预览']} <span style="color:gray; font-size:12px;">({row['字数']}字)</span>
                            </div>
                            """, unsafe_allow_html=True)

                    with col_b:
                        st.subheader("🎬 分镜编辑区 (可手动微调)")
                        st.text_area("分镜结果内容", value=result, height=800)
                        st.download_button("💾 下载分镜稿", result, "storyboard_v8.txt")

            except Exception as e:
                st.error(f"导演系统报错：{str(e)}")
