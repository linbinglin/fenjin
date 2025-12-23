import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 核心工具函数：智能语义拆分 ---
def smart_chunk_text(text, max_chars=1200):
    """寻找句号或换行符进行智能切分，防止语义断裂"""
    chunks = []
    while len(text) > max_chars:
        # 在截断点附近找最后一个句号、感叹号或问号
        split_index = -1
        for mark in ["。", "！", "？", "\n"]:
            pos = text.rfind(mark, 0, max_chars)
            split_index = max(split_index, pos)
        
        # 如果没找到标点，就强行截断
        if split_index == -1:
            split_index = max_chars
        else:
            split_index += 1 # 包含标点符号本身
            
        chunks.append(text[:split_index])
        text = text[split_index:]
    chunks.append(text)
    return chunks

def get_pure_text(text):
    """提取纯文本内容，用于精确对账"""
    text = re.sub(r'\d+[\.、]\s*', '', text)
    return "".join(text.split())

# --- 页面配置 ---
st.set_page_config(page_title="解说分镜导演 V10-万能适配版", layout="wide")

st.sidebar.title("⚙️ 核心引擎配置")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.success("""
**🎞️ V10 核心升级点：**
1. **智能分块**：按句号切割，解决幻觉重复。
2. **长句重构**：优化长难句的分镜逻辑。
3. **万能适配**：不再局限于特定题材，适配全网文案。
""")

# --- 主界面 ---
st.title("🎞️ 全能文案·工业级分镜系统 (V10)")
st.caption("版本 10.0 | 解决分段重复、语义理解不足、字数溢出问题。")

uploaded_file = st.file_uploader("📂 上传文案文件 (.txt)", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    st.subheader("📊 文案逻辑稽核面板")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 启动语义无损分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                # 步骤 1：智能分块
                chunks = smart_chunk_text(input_stream)
                st.write(f"📦 已根据语义锚点拆分为 {len(chunks)} 个任务块，正在逐块分析...")
                
                full_result = []
                current_shot_idx = 1
                
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    with st.spinner(f'正在分析第 {idx+1}/{len(chunks)} 块语义...'):
                        # --- V10 万能导演 Prompt ---
                        system_prompt = f"""你是一个顶级的解说导演。任务：将文本流转换为适合5秒画面的分镜脚本。

【绝对准则】：
1. **0 字偏差提取**：你必须按照原文顺序，逐字逐句进行搬运，严禁自行添加任何润色词、引导词或重复前一段的内容。
2. **35字黄金律**：单行字数必须在 20-35 字之间。若原句过长（如超过35字），必须在逻辑转折处拆分为两行。
3. **语义聚合（拒绝碎镜）**：严禁无意义的超短句。如果一句话不到 15 字，必须与后文合并。
4. **长句处理逻辑**：遇到描述性的长句（如“限她三天之内交出来...”），要根据视觉动作的连贯性进行分行，保证配音与画面的平衡感。
5. **万能适配**：无视题材，核心目标是“字数填满”与“动作完整”。

【输出要求】：
从编号 {current_shot_idx} 开始输出。严禁任何前言或总结词。"""

                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": f"请对此文本段落进行分镜（绝对禁止重复前文）：\n\n{chunk}"}
                            ],
                            temperature=0, 
                        )
                        
                        chunk_res = response.choices[0].message.content
                        full_result.append(chunk_res)
                        
                        # 动态更新编号
                        last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                        if last_nums:
                            current_shot_idx = int(last_nums[-1]) + 1
                        
                        progress_bar.progress((idx + 1) / len(chunks))

                # 最终拼接与统计
                final_result = "\n".join(full_result)
                output_stream = get_pure_text(final_result)
                output_len = len(output_stream)
                
                lines = [l.strip() for l in final_result.split('\n') if re.match(r'^\d+', l.strip())]
                count = len(lines)
                
                # 数据分析
                analysis_data = []
                for i, line in enumerate(lines):
                    content = re.sub(r'^\d+[\.、]\s*', '', line)
                    ln = len(content)
                    status = "✅ 理想" if 20 <= ln <= 35 else "⚠️ 调整"
                    analysis_data.append({"序号": i+1, "预览": content[:20], "字数": ln, "状态": status})
                df = pd.DataFrame(analysis_data)

                # 更新看板
                m2.metric("生成分镜总数", f"{count} 组")
                m3.metric("最终还原字数", f"{output_len} 字")
                diff = output_len - input_len
                m4.metric("字数偏差", f"{diff} 字")

                st.divider()

                # UI 展示
                c_a, c_b = st.columns([2, 1])
                with c_a:
                    st.subheader("📝 深度分镜编辑器 (无损还原)")
                    if diff == 0: st.success("✅ 100% 像素级对齐")
                    else: st.warning(f"偏差值 {diff}：通常源于标点转换或极个别重复，请检查段落交界处。")
                    st.text_area("分镜脚本正文", value=final_result, height=600)

                with c_b:
                    st.subheader("📊 节奏节奏实时分析")
                    st.dataframe(df, use_container_width=True)
                    st.metric("平均每镜停留", f"{output_len/count:.1f} 字")
                    st.download_button("💾 下载最终分镜稿", final_result, "V10_Final.txt")

            except Exception as e:
                st.error(f"处理出错：{str(e)}")
