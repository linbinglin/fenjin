import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 工具函数 ---
def get_pure_text(text):
    """提取纯文本内容，用于字数校验"""
    text = re.sub(r'\d+[\.、]\s*', '', text)
    return "".join(text.split())

# --- 页面配置 ---
st.set_page_config(page_title="解说分镜导演 Pro V5", layout="wide")

st.sidebar.title("⚙️ 导演工作台配置")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.warning("""
**🎞️ 分镜刚性指标：**
1. **35字红线**：单行绝对严禁超过35字。
2. **0偏差还原**：原文一个字都不能少。
3. **节奏感**：理想长度为 25-32 字。
""")

# --- 主界面 ---
st.title("🎞️ 电影解说·像素级分镜系统 (V5 高性能版)")
st.info("已解决：漏字问题。本次优化：解决单镜过长（超35字）问题。")

uploaded_file = st.file_uploader("📂 上传文案 (.txt)", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    # 顶层看板
    st.subheader("📊 文案稽核数据")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("待处理总字数", f"{input_len} 字")

    if st.button("🚀 启动深度语义聚合分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                with st.spinner('正在进行像素级拆解与字数严控...'):
                    # --- V5 强化版 Prompt：加入硬性的字数切分逻辑 ---
                    system_prompt = f"""你是一个高精度电影解说导演。
任务：将文本拆分为编号分镜，必须同时满足“零字数偏差”和“短小精悍”两个要求。

【硬性红线 - 必须执行】：
1. **35字物理极限**：每个编号的内容严禁超过 35 个字符。这是为了配合 5 秒的画面节奏。
2. **像素还原**：你是原文的搬运工。严禁删减、修改、合并或总结原文。字数偏差必须为 0。
3. **强行拆分逻辑**：
   - 如果一句话（从标点到标点）超过了 35 字，你必须在中间寻找逻辑点（如逗号或词语间隙）强行断开，分为两个编号。
   - 示例：原句有 50 字，你必须拆成 25+25 或 30+20 的两组分镜。
4. **视觉切分点**：
   - 只要单行字数达到 25-35 字，即便句子没写完，也优先建议另起一行。
   - 对话切换、大动作出现，必须换行。
5. **万能适配**：此指令适用于任何题材（小说、解说、科普、广告）。

【输出格式】：
1.内容内容（严禁任何描述性括号）
2.内容内容
..."""

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请像素级拆解以下文本，确保单行严格在35字以内，不漏字：\n\n{input_stream}"}
                        ],
                        temperature=0, 
                    )

                    result = response.choices[0].message.content
                    output_stream = get_pure_text(result)
                    output_len = len(output_stream)
                    
                    # 分析每一行
                    lines = [l.strip() for l in result.split('\n') if re.match(r'^\d+', l.strip())]
                    count = len(lines)
                    
                    # 准备表格数据
                    analysis_data = []
                    for i, line in enumerate(lines):
                        content = re.sub(r'^\d+[\.、]\s*', '', line)
                        length = len(content)
                        status = "✅ 正常" if length <= 35 else "❌ 太长(必断)"
                        analysis_data.append({"序号": i+1, "内容预览": content[:20]+"...", "长度": length, "状态": status})
                    df = pd.DataFrame(analysis_data)

                    # 更新看板
                    m2.metric("生成分镜总数", f"{count} 组")
                    m3.metric("处理后总字数", f"{output_len} 字")
                    diff = output_len - input_len
                    m4.metric("字数偏差", f"{diff} 字")

                    st.divider()

                    # 校验结果展示
                    col_res, col_table = st.columns([2, 1])
                    
                    with col_res:
                        st.subheader("✍️ 分镜编辑区")
                        if diff == 0:
                            st.success("✅ 字数对齐：文字 100% 还原。")
                        else:
                            st.error(f"❌ 还原偏差：{diff} 字。")
                        
                        st.text_area("直接复制结果", value=result, height=600)

                    with col_table:
                        st.subheader("📊 实时节奏分析")
                        st.table(df)
                        
                    st.download_button("💾 下载最终脚本", result, "final_storyboard.txt")

            except Exception as e:
                st.error(f"处理失败：{str(e)}")
