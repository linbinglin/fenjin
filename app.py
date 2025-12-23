import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 核心工具函数：重排列序号 ---
def reindex_storyboard(text):
    """
    不管用户如何删除或增加换行，一键重新从 1 开始排列所有序号
    """
    # 移除原本可能存在的序号（支持 数字. 或 数字、）
    lines = text.split('\n')
    new_lines = []
    count = 1
    for line in lines:
        # 去掉每行开头的数字和标点
        clean_line = re.sub(r'^\d+[\.、]\s*', '', line).strip()
        if clean_line:
            new_lines.append(f"{count}.{clean_line}")
            count += 1
    return "\n".join(new_lines)

# --- 核心工具函数：智能语义分块 ---
def smart_chunk_text(text, max_chars=1000):
    chunks = []
    while len(text) > max_chars:
        split_index = -1
        for mark in ["\n", "。", "！", "？"]:
            pos = text.rfind(mark, 0, max_chars)
            split_index = max(split_index, pos)
        if split_index == -1:
            split_index = max_chars
        else:
            split_index += 1
        chunks.append(text[:split_index].strip())
        text = text[split_index:]
    chunks.append(text.strip())
    return [c for c in chunks if c]

def get_pure_text(text):
    text = re.sub(r'\d+[\.、]\s*', '', text)
    return "".join(text.split())

# --- 页面配置 ---
st.set_page_config(page_title="解说分镜导演 Pro V12 (人机协作版)", layout="wide")

# --- 侧边栏配置 ---
st.sidebar.title("⚙️ 导演引擎配置")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.markdown("""
**🎞️ V12 协作准则：**
1. **AI 初剪**：基于视觉主语切换。
2. **人工精剪**：支持在下方编辑器直接修改文案或换行。
3. **一键重排**：修改后点击“校准序号”，序号自动对齐。
""")

# --- 主界面 ---
st.title("🎞️ 全能文案·人机协同分镜系统 (V12)")
st.caption("版本 12.0 | AI 深度规划 + 人工后期精修 | 支持一键自动重排序号")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

# 使用 Session State 存储分镜结果，以便用户微调
if 'storyboard_draft' not in st.session_state:
    st.session_state.storyboard_draft = ""

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    # 监控面板
    st.subheader("📊 创作数据稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    # --- 逻辑 A：AI 自动化分镜 ---
    if st.button("🚀 启动 AI 初步分镜"):
        if not api_key:
            st.error("请配置 API 参数")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                chunks = smart_chunk_text(input_stream)
                
                full_result = []
                current_shot_idx = 1
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    with st.spinner(f'正在分析第 {idx+1}/{len(chunks)} 段语义...'):
                        # V12 指令：强化“人称/行为”独立性
                        system_prompt = f"""你是一个顶级的解说导演。
【视觉独立原则】：
1. 角色台词与他的内心独白或他人反应必须拆分为不同编号。
2. 一个分镜只允许一个核心主语动作，主语切换必须切分镜。
3. 像素级还原，严禁漏字或重复。
4. 目标 25-35 字，严禁超过 35 字。
输出格式：从编号 {current_shot_idx} 开始，仅输出编号列表。"""

                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "system_prompt": system_prompt},
                                {"role": "user", "content": f"请对此段落进行视觉单元分镜：\n\n{chunk}"}
                            ],
                            temperature=0, 
                        )
                        chunk_res = response.choices[0].message.content.strip()
                        full_result.append(chunk_res)
                        last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                        if last_nums:
                            current_shot_idx = int(last_nums[-1]) + 1
                        progress_bar.progress((idx + 1) / len(chunks))

                st.session_state.storyboard_draft = "\n".join(full_result)
                st.success("AI 分镜初稿生成完毕！请在下方进行人工精修。")

            except Exception as e:
                st.error(f"处理失败：{str(e)}")

    # --- 逻辑 B：人工微调区 ---
    if st.session_state.storyboard_draft:
        st.divider()
        st.subheader("✍️ 人工精修编辑器")
        
        col_edit, col_analyze = st.columns([2, 1])
        
        with col_edit:
            # 用户在此处通过回车/删除进行编辑
            edited_text = st.text_area(
                "在此微调文案内容（按回车增加分镜，删除换行合并分镜）：", 
                value=st.session_state.storyboard_draft, 
                height=600,
                key="editor"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.button("🔢 一键校准序号"):
                st.session_state.storyboard_draft = reindex_storyboard(edited_text)
                st.rerun()
                
            if col_btn2.download_button("💾 下载最终分镜稿", st.session_state.storyboard_draft, "storyboard_final.txt"):
                st.balloons()

        with col_analyze:
            # 实时数据看板
            pure_out = get_pure_text(st.session_state.storyboard_draft)
            out_len = len(pure_out)
            diff = out_len - input_len
            
            lines = [l for l in st.session_state.storyboard_draft.split('\n') if re.match(r'^\d+', l.strip())]
            
            st.metric("最终分镜总数", f"{len(lines)} 组")
            st.metric("最终还原字数", f"{out_len} 字")
            
            if diff == 0: st.success("✅ 字数对齐")
            else: st.error(f"❌ 字数偏差: {diff}")
            
            # 节奏列表预览
            analysis_list = []
            for i, line in enumerate(lines):
                c = re.sub(r'^\d+[\.、]\s*', '', line)
                analysis_list.append({"镜头": i+1, "长度": len(c), "状态": "✅" if len(c) <= 35 else "❌太长"})
            st.dataframe(pd.DataFrame(analysis_list), height=400)
