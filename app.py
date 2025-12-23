import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# ==========================================
# 1. 核心工具函数
# ==========================================

def get_pure_text(text):
    """提取纯文本内容，排除编号和空格，用于 1:1 精确对账"""
    if not text: return ""
    # 移除行首编号（匹配 数字. 或 数字、 或 数字 ）
    text = re.sub(r'^\s*\d+[\.、\s]\s*', '', text, flags=re.MULTILINE)
    # 移除所有空白符
    return "".join(text.split())

def reindex_text(text):
    """一键重排序号，支持人工增删分镜后的快速修复"""
    lines = text.split('\n')
    valid_lines = []
    count = 1
    for line in lines:
        content = re.sub(r'^\s*\d+[\.、\s]\s*', '', line).strip()
        if content:
            valid_lines.append(f"{count}.{content}")
            count += 1
    return "\n".join(valid_lines)

def smart_chunk_text(text, max_chars=1200):
    """智能语义分段：确保任务块切在句号处，防止AI产生内容重复"""
    chunks = []
    while len(text) > max_chars:
        split_index = -1
        # 寻找最近的句子结束标志
        for mark in ["\n", "。", "！", "？"]:
            pos = text.rfind(mark, 0, max_chars)
            split_index = max(split_index, pos)
        
        if split_index == -1: split_index = max_chars
        else: split_index += 1 
            
        chunks.append(text[:split_index].strip())
        text = text[split_index:]
    if text: chunks.append(text.strip())
    return [c for c in chunks if c]

# ==========================================
# 2. 页面配置与初始化
# ==========================================

st.set_page_config(page_title="解说分镜 Pro V16", layout="wide")

if 'final_storyboard' not in st.session_state:
    st.session_state.final_storyboard = ""
if 'original_text_clean' not in st.session_state:
    st.session_state.original_text_clean = ""

# --- 侧边栏配置 ---
with st.sidebar:
    st.title("⚙️ 引擎配置中心")
    api_key = st.text_input("1. API Key", type="password")
    
    # URL 逻辑修复：这里不再自动加 /v1，让用户输入什么就是什么
    base_url_input = st.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
    
    st.markdown("**3. Model ID**")
    model_id = st.text_input("模型名称", value="gpt-4o", help="千万不要填错误的名称，推荐 gpt-4o")
    
    st.divider()
    st.info("""
    **🎞️ 导演手册：**
    - 0 字损耗还原。
    - 每镜 25-35 字，节奏黄金平衡。
    - **万能适配**：小说、散文、解说、科普通用。
    """)

# ==========================================
# 3. 主界面逻辑
# ==========================================

st.title("🎬 电影解说·万能分镜导演系统 (V16)")
uploaded_file = st.file_uploader("📂 选择文案 TXT 文件", type=['txt'])

if uploaded_file:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    # 锁定原文进行稽核
    st.session_state.original_text_clean = "".join(raw_text.split())
    input_len = len(st.session_state.original_text_clean)

    st.subheader("📊 文案逻辑稽核看板")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 启动语义无损分镜"):
        if not api_key:
            st.error("请输入 API Key")
        else:
            try:
                # 【路径修复关键点】：彻底清理 URL，防止重复 v1/v1
                clean_url = base_url_input.strip()
                if clean_url.endswith('/'): clean_url = clean_url[:-1]
                
                client = OpenAI(api_key=api_key, base_url=clean_url)
                
                # 开始分块处理
                chunks = smart_chunk_text(st.session_state.original_text_clean)
                st.write(f"📦 文本已根据语义锚点拆分为 {len(chunks)} 个任务块，正在处理...")
                
                all_results = []
                current_idx = 1
                prog = st.progress(0)
                
                for i, chunk in enumerate(chunks):
                    with st.spinner(f"正在处理第 {i+1} 块内容..."):
                        # V16 导演指令：万能叙事逻辑
                        prompt = f"""你是一个高级解说分镜导演。
【分镜聚合原则】：
1. **0 损镜像还原**：必须 1:1 输出原文文字。不准删减、重复、润色。
2. **黄金平衡长度**：单行目标 25-35 字。
   - 严禁出现低于 15 字的碎句。如果一句话很短，必须与前后文合并。
   - 如果一句话超长，必须在逗号或语义点强行截断。
3. **视觉驱动**：主语切换（人称换人）或台词结束必须切分镜。
4. **编号锚点**：从编号 {current_idx} 开始。
待处理文本流：
{chunk}"""
                        
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": "你只输出带编号的分镜列表，禁止任何废话。"},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0
                        )
                        chunk_res = response.choices[0].message.content.strip()
                        all_results.append(chunk_res)
                        
                        # 动态更新下一块起始编号
                        nums = re.findall(r'(\d+)[\.、]', chunk_res)
                        if nums: current_idx = int(nums[-1]) + 1
                        prog.progress((i+1)/len(chunks))
                
                st.session_state.final_storyboard = "\n".join(all_results)
                st.success("导演规划完毕！")
            except Exception as e:
                st.error(f"处理失败: {str(e)}")

# ==========================================
# 4. 编辑与监控区
# ==========================================

if st.session_state.final_storyboard:
    st.divider()
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.subheader("✍️ 导演精修区")
        edited_text = st.text_area(
            "可在下方手动增减内容（回车分镜，删除合并）：",
            value=st.session_state.final_storyboard,
            height=600
        )
        
        c1, c2 = st.columns(2)
        if c1.button("🔢 校准所有分镜序号"):
            st.session_state.final_storyboard = reindex_text(edited_text)
            st.rerun()
            
        c2.download_button("💾 下载全本分镜稿", st.session_state.final_storyboard, "storyboard_final.txt")

    with col_r:
        st.subheader("📊 实时节奏分析")
        current_clean = get_pure_text(st.session_state.final_storyboard)
        curr_len = len(current_clean)
        diff = curr_len - len(st.session_state.original_text_clean)
        
        shot_lines = [l for l in st.session_state.final_storyboard.split('\n') if re.match(r'^\d+', l.strip())]
        
        st.metric("生成分镜总数", f"{len(shot_lines)} 组")
        st.metric("当前还原字数", f"{curr_len} 字")
        
        if diff == 0: st.success("✅ 字数对齐")
        else: st.error(f"❌ 偏差：{diff} 字")

        # 节奏分析表
        analysis = []
        for i, line in enumerate(shot_lines):
            txt = re.sub(r'^\d+[\.、\s]\s*', '', line)
            ln = len(txt)
            analysis.append({"镜头": i+1, "字数": ln, "状态": "✅" if 15 <= ln <= 35 else "⚠️调节奏"})
        
        st.dataframe(pd.DataFrame(analysis), height=400, use_container_width=True)
