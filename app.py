import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 工具函数：智能语义分块 (V11 增强版) ---
def smart_chunk_text(text, max_chars=1000):
    """寻找最稳固的标点符号（。！？\n）进行切分，确保每一块都是完整的段落"""
    chunks = []
    while len(text) > max_chars:
        split_index = -1
        # 优先找段落末尾，其次是长句末尾
        for mark in ["\n", "。", "！", "？"]:
            pos = text.rfind(mark, 0, max_chars)
            split_index = max(split_index, pos)
        
        if split_index == -1:
            split_index = max_chars
        else:
            split_index += 1 # 包含标点符号
            
        chunks.append(text[:split_index].strip())
        text = text[split_index:]
    chunks.append(text.strip())
    return [c for c in chunks if c]

def get_pure_text(text):
    """精确提取纯文本内容，用于 1:1 对账"""
    text = re.sub(r'\d+[\.、]\s*', '', text)
    return "".join(text.split())

# --- 页面配置 ---
st.set_page_config(page_title="电影解说导演 V11-视觉单元版", layout="wide")

st.sidebar.title("⚙️ 导演引擎 V11")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.info("""
**🎞️ V11 视觉切分准则：**
1. **主语即镜头**：人称切换（如“我”转“他”）必须断开。
2. **动作即分镜**：一个核心动作完成后必须切镜。
3. **对话独立性**：台词结束后的动作描写严禁混在一起。
4. **硬性 35 字**：单行依然禁止超过 35 字。
""")

# --- 主界面 ---
st.title("🎞️ 全能文案·电影感分镜系统 (V11)")
st.caption("针对“音画不同步”、“内容重叠”深度优化。适配全题材文案。")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    st.subheader("📊 视觉逻辑稽核面板")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 启动视觉无损分镜"):
        if not api_key:
            st.error("请配置侧边栏参数")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                # 步骤 1：智能分块
                chunks = smart_chunk_text(input_stream)
                st.write(f"📦 已识别 {len(chunks)} 个独立剧情块，正在进行视觉单元规划...")
                
                full_result = []
                current_shot_idx = 1
                
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    with st.spinner(f'正在规划第 {idx+1}/{len(chunks)} 块镜头...'):
                        # --- V11 视觉导演 Prompt ---
                        system_prompt = f"""你是一个顶级的解说视频导演。你的任务是把文本流拆解成“画面镜头”。

【视觉分镜红线】：
1. **主语变更即切分**：只要句子的主语（动作发出者）发生了改变，必须立即结束当前分镜，开启下一个编号。
2. **台词与动作分离**：角色的一句台词结束后，紧接的其他角色的反应或环境描写，严禁放在同一个编号内。
3. **镜像 0 损还原**：你只是负责加编号和换行。严禁擅自修改、润色、重复、或合并原文任何文字。偏差必须为 0。
4. **长度与语意平衡**：
   - 理想长度：25-35 字。
   - 强制上限：35 字。若单句台词超长，请在不漏字的前提下在语气点强行拆分。
5. **拒绝碎片化**：在主语未变、动作连贯的前提下，尽量填满 25-35 字。

【输出要求】：
- 从编号 {current_shot_idx} 开始。
- 严禁任何解释、括号、画面词，只输出“数字.文案”。"""

                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": f"请对此文本块进行视觉单元分镜，严禁重复和漏字：\n\n{chunk}"}
                            ],
                            temperature=0, 
                        )
                        
                        chunk_res = response.choices[0].message.content.strip()
                        full_result.append(chunk_res)
                        
                        # 更新下一块的起始编号
                        last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                        if last_nums:
                            current_shot_idx = int(last_nums[-1]) + 1
                        
                        progress_bar.progress((idx + 1) / len(chunks))

                # 数据合并与展示
                final_result = "\n".join(full_result)
                output_stream = get_pure_text(final_result)
                output_len = len(output_stream)
                
                lines = [l.strip() for l in final_result.split('\n') if re.match(r'^\d+', l.strip())]
                count = len(lines)
                
                analysis_data = []
                for i, line in enumerate(lines):
                    content = re.sub(r'^\d+[\.、]\s*', '', line)
                    ln = len(content)
                    status = "✅ 理想" if 20 <= ln <= 35 else ("❌ 过长" if ln > 35 else "🟡 偏短")
                    analysis_data.append({"序号": i+1, "内容预览": content[:20], "长度": ln, "状态": status})
                df = pd.DataFrame(analysis_data)

                # 看板更新
                m2.metric("生成分镜总数", f"{count} 组")
                m3.metric("处理后总字数", f"{output_len} 字")
                diff = output_len - input_len
                m4.metric("偏差值", f"{diff} 字", delta_color="inverse")

                st.divider()

                # UI 交互
                c_a, c_b = st.columns([2, 1])
                with c_a:
                    st.subheader("🎬 视觉分镜编辑器 (无损还原)")
                    if diff == 0: st.success("✅ 100% 镜像还原成功")
                    else: st.error(f"⚠️ 偏差：{diff} 字。提示：正数为重复/脑补，负数为漏字。")
                    st.text_area("分镜正文", value=final_result, height=600)

                with c_b:
                    st.subheader("📊 实时视觉节奏分析")
                    st.dataframe(df, use_container_width=True)
                    st.metric("平均每镜停留", f"{output_len/count:.1f} 字")
                    st.download_button("💾 下载最终分镜稿", final_result, "storyboard_v11.txt")

            except Exception as e:
                st.error(f"导演系统运行出错：{str(e)}")
