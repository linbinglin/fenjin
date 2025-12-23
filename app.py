import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 核心辅助函数 ---
def get_pure_text(text):
    """提取纯文本，用于最终字数对账"""
    # 移除分镜编号
    text = re.sub(r'\d+[\.、]\s*', '', text)
    # 移除所有不可见字符、换行、空格
    return "".join(text.split())

# --- 页面配置 ---
st.set_page_config(page_title="解说分镜导演 Pro V7", layout="wide")

st.sidebar.title("⚙️ 导演引擎配置")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.info("""
**🎞️ V7 逻辑坐标准则：**
1. **顺序第一**：严禁打乱原文逻辑顺序。
2. **硬性上限**：35字符（强制），不达标宁愿留空。
3. **语义聚合**：短句合并，保持解说节奏。
4. **0字丢失**：像素级对齐原文。
""")

# --- 主界面 ---
st.title("🎞️ 电影解说·逻辑无损分镜系统 (V7)")
st.caption("当前版本：解决“分镜与文案不契合”、“文字重叠”及“漏字”问题。")

uploaded_file = st.file_uploader("📂 上传文案 (.txt)", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    # 预处理：保留原文字符，但清理多余空行，作为“有序字符流”
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    # 监控面板
    st.subheader("📊 文案逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 启动逻辑无损分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                # 规范化 URL
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                with st.spinner('导演正在根据逻辑坐标重新排版...'):
                    # --- V7 核心指令：引入顺序坐标与物理截断 ---
                    system_prompt = """你是一个顶级视觉导演。任务：将文本流拆分为解说分镜。

【执行准则 - 严禁妥协】：
1. **逻辑顺序（最高优先级）**：你必须严格按照文本出现的先后顺序进行处理。严禁跳跃、重复、或倒置原文内容。
2. **35字物理死线**：每一行（每一个分镜）的文字总数绝对不能超过 35 个字符。这是为了 5 秒音频的刚性对齐。
3. **内容完整性（0偏差）**：严禁删减、修改、合并语义。你只是一个带编号的“文本搬运工”。字数偏差必须为 0。
4. **分镜聚合逻辑**：
   - 寻找自然的停顿点（。！？，）进行聚合。
   - 如果几个短句合并后未超过 35 字，请务必合并为一行，以保持节奏。
   - 如果一句话很长，请在不漏字的前提下，寻找逻辑点切分为两行。
5. **万能适配**：无视文本题材，只按“文本流 -> 35字内聚合 -> 编号输出”逻辑执行。

【输出示例】：
1.内容内容
2.内容内容
(不要输出任何括号、画面描述或解释性文字)"""

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文本流进行有序的 35 字内分镜拆解，确保 0 漏字：\n\n{input_stream}"}
                        ],
                        temperature=0, 
                    )

                    result = response.choices[0].message.content
                    output_stream = get_pure_text(result)
                    output_len = len(output_stream)
                    
                    # 结果行分析
                    lines = [l.strip() for l in result.split('\n') if re.match(r'^\d+', l.strip())]
                    count = len(lines)
                    
                    # 动态分析每行质量
                    analysis_data = []
                    for i, line in enumerate(lines):
                        content = re.sub(r'^\d+[\.、]\s*', '', line)
                        ln = len(content)
                        analysis_data.append({
                            "序号": i+1, 
                            "内容预览": content[:25], 
                            "字数": ln, 
                            "状态": "✅" if ln <= 35 else "❌"
                        })
                    df = pd.DataFrame(analysis_data)

                    # 更新看板
                    m2.metric("分镜总数", f"{count} 组")
                    m3.metric("还原字数", f"{output_len} 字")
                    diff = output_len - input_len
                    m4.metric("偏差", f"{diff} 字")

                    st.divider()

                    # 展示区
                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        st.subheader("✍️ 分镜结果预览")
                        if diff == 0: st.success("🎉 100% 像素级对齐")
                        else: st.error(f"⚠️ 偏差：{diff} 字")
                        st.text_area("直接复制结果", value=result, height=600)

                    with col_b:
                        st.subheader("📊 节奏节奏分析")
                        st.dataframe(df, use_container_width=True)
                        avg = output_len / count if count > 0 else 0
                        st.metric("平均每镜字数", f"{avg:.1f}")
                        if avg > 35: st.error("警告：平均字数超标！")

                    st.download_button("💾 下载分镜脚本", result, "final_script_v7.txt")

            except Exception as e:
                st.error(f"处理失败：{str(e)}")
