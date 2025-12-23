import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 工具函数 ---
def get_pure_text(text):
    text = re.sub(r'\d+[\.、]\s*', '', text)
    return "".join(text.split())

# --- 页面配置 ---
st.set_page_config(page_title="解说分镜导演 Pro V6", layout="wide")

st.sidebar.title("⚙️ 导演工作台配置")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.info("""
**🎞️ V6 核心逻辑 (满载聚合)：**
1. **单镜上限**：35 字符。
2. **拒绝碎片**：除非是动作剧变，否则 15 字以下的句子必须与后文合并。
3. **填满 5 秒**：目标是让每行接近 25-35 字，使画面与配音节奏完美对齐。
""")

# --- 主界面 ---
st.title("🎞️ 电影解说·像素级分镜系统 (V6 节奏优化版)")
st.caption("已解决：漏字（0偏差）。本次优化：解决分镜太碎、画面跳动过快问题。")

uploaded_file = st.file_uploader("📂 上传文案 (.txt)", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    # 顶层看板
    st.subheader("📊 文案稽核数据")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 启动深度语义聚合分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                # 规范化 URL
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                with st.spinner('正在进行高密度语义聚合...'):
                    # --- V6 满载聚合 Prompt ---
                    system_prompt = f"""你是一个顶级的解说导演。任务：将文本拆分为分镜。要求极致的字数利用率和 0 字数损失。

【分镜聚合逻辑 - 核心执行】：
1. **0 字损失**：严禁删减、总结、改写原文。字数偏差必须为 0。
2. **35 字封顶原则**：单行分镜严禁超过 35 字。
3. **满载率要求（拒绝碎片化）**：
   - 目标：让每个编号里的字数尽量接近 30 字。
   - 聚合：如果一句话（如“在宫墙下”）只有几个字，**必须**强制与前一句合并，除非合并后总字数超过了 35 字。
   - 严禁出现大量只有 10 个字的分镜。你要像填桶一样，尽量装满 35 字后再换下一个桶。
4. **切分触发点**：
   - 当前分镜字数即将超过 35 字。
   - 对话的角色发生了切换。
   - 一个核心的大动作转换。
5. **万能适配**：此指令适配任何文案，核心是“字数填满”与“动作切换”的平衡。

【输出格式】：
1.内容内容
2.内容内容
（禁止输出任何多余符号或描述）"""

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文本进行 0 偏差分镜，尽量让每行填满 30-35 字，不要太碎：\n\n{input_stream}"}
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
                        status = "✅ 理想" if 25 <= length <= 35 else ("⚠️ 略碎" if length < 25 else "❌ 过长")
                        analysis_data.append({"序号": i+1, "预览": content[:20]+"...", "长度": length, "状态": status})
                    df = pd.DataFrame(analysis_data)

                    # 更新看板
                    m2.metric("生成分镜总数", f"{count} 组")
                    m3.metric("还原后字数", f"{output_len} 字")
                    diff = output_len - input_len
                    m4.metric("字数偏差", f"{diff} 字")

                    st.divider()

                    # 结果区
                    col_res, col_table = st.columns([2, 1])
                    with col_res:
                        st.subheader("✍️ 分镜编辑器")
                        if diff == 0: st.success("✅ 字数对齐：100% 还原")
                        else: st.error(f"❌ 偏差：{diff} 字")
                        st.text_area("分镜结果内容", value=result, height=600)

                    with col_table:
                        st.subheader("📊 节奏节奏分析")
                        st.dataframe(df, use_container_width=True)
                        avg_len = output_len / count if count > 0 else 0
                        st.metric("平均每镜字数", f"{avg_len:.1f}")
                        if avg_len < 20: st.warning("提示：分镜依然偏碎，建议检查模型是否过于保守。")

                    st.download_button("💾 下载分镜脚本", result, "script_v6.txt")

            except Exception as e:
                st.error(f"处理失败：{str(e)}")
