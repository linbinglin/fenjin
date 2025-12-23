import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 核心工具函数 ---
def get_pure_text(text):
    """极致纯净提取，用于对账"""
    text = re.sub(r'\d+[\.、]\s*', '', text)
    return "".join(text.split())

def chunk_text(text, chunk_size=1200):
    """将超长文拆分成小块，防止AI中断和幻觉"""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# --- 页面配置 ---
st.set_page_config(page_title="全能分镜导演 V9-长文无损版", layout="wide")

st.sidebar.title("⚙️ 导演引擎配置")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.warning("""
**🎞️ V9 工业级准则：**
1. **自动分段处理**：解决长文中断问题。
2. **35字强硬死线**：单行必断，严禁超标。
3. **镜像零损**：严禁重复，严禁漏字。
""")

# --- 主界面 ---
st.title("🎞️ 全能文案·工业级无损分镜系统")
st.caption("针对超长文案（4000字+）优化，解决幻觉重复、中途断更、分镜过长问题。")

uploaded_file = st.file_uploader("📂 上传长文案 (.txt)", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    st.subheader("📊 逻辑稽核面板")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 开启无损分段分镜处理"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                # 步骤 1：分段
                chunks = chunk_text(input_stream)
                st.write(f"📦 检测到长文本，已自动拆分为 {len(chunks)} 个任务块并行处理...")
                
                full_result = []
                current_shot_idx = 1
                
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    with st.spinner(f'正在处理第 {idx+1}/{len(chunks)} 块内容...'):
                        # --- V9 镜像聚合 Prompt ---
                        system_prompt = f"""你是一个电影解说分镜师，负责将文本流无损地转换为分镜。
                        
【绝对准则】：
1. **镜像还原**：你只是一个搬运工，严禁删减、修改、润色或总结原文！一个字都不能多，一个字都不能少！
2. **35字硬性截断**：单个分镜（一行）的内容字数必须控制在 20-35 字之间。绝对严禁超过 35 字！
3. **拒绝重复**：严格按照输入顺序处理，严禁在不同分镜中重复出现相同的句子。
4. **聚合逻辑**：
   - 寻找自然的标点符号（，。！？）作为优先切分点。
   - 如果几个短句合并后未超过 35 字，必须合并以保持解说节奏。
   - 如果原句太长，必须强行在逻辑点切开。

【输出格式】：
从编号 {current_shot_idx} 开始编号。直接输出编号列表。"""

                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": f"请处理以下文本段落：\n\n{chunk}"}
                            ],
                            temperature=0, 
                        )
                        
                        chunk_res = response.choices[0].message.content
                        full_result.append(chunk_res)
                        
                        # 更新下一个块的起始编号
                        last_idx_match = re.findall(r'(\d+)[\.、]', chunk_res)
                        if last_idx_match:
                            current_shot_idx = int(last_idx_match[-1]) + 1
                        
                        progress_bar.progress((idx + 1) / len(chunks))

                # 合并结果
                final_result = "\n".join(full_result)
                output_stream = get_pure_text(final_result)
                output_len = len(output_stream)
                
                # 行分析
                lines = [l.strip() for l in final_result.split('\n') if re.match(r'^\d+', l.strip())]
                count = len(lines)
                
                analysis_data = []
                for i, line in enumerate(lines):
                    content = re.sub(r'^\d+[\.、]\s*', '', line)
                    ln = len(content)
                    status = "✅ 理想" if 20 <= ln <= 35 else "❌ 不佳"
                    analysis_data.append({"序号": i+1, "预览": content, "长度": ln, "状态": status})
                df = pd.DataFrame(analysis_data)

                # 更新看板
                m2.metric("生成分镜总数", f"{count} 组")
                m3.metric("还原字_纯净", f"{output_len} 字")
                diff = output_len - input_len
                m4.metric("偏差值", f"{diff} 字")

                st.divider()

                # 展示
                c_a, c_b = st.columns([1.5, 1])
                with c_a:
                    st.subheader("📝 分镜结果预览 (无损版)")
                    if diff == 0: st.success("🎉 字数 100% 对齐，已处理至结局！")
                    else: st.warning(f"⚠️ 偏差：{diff} 字。请检查段落接缝处是否有多余文字。")
                    st.text_area("分镜编辑器", value=final_result, height=800)

                with c_b:
                    st.subheader("📊 节奏节奏实时分析")
                    st.dataframe(df, use_container_width=True)
                    st.download_button("💾 下载全本分镜稿", final_result, "storyboard_v9.txt")

            except Exception as e:
                st.error(f"处理失败：{str(e)}")
