import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# ==========================================
# 1. 核心工具函数 (必须放在代码最前面防止 NameError)
# ==========================================

def get_pure_text(text):
    """提取纯文本内容，用于精确对账"""
    if not text:
        return ""
    # 移除行首编号（匹配 数字. 或 数字、 或 数字 ）
    text = re.sub(r'^\s*\d+[\.、\s]\s*', '', text, flags=re.MULTILINE)
    # 移除所有空白符、换行、空格
    return "".join(text.split())

def reindex_text(text):
    """人工微调后的序号自动重排系统"""
    lines = text.split('\n')
    valid_lines = []
    count = 1
    for line in lines:
        # 移除已有的任何序号格式
        content = re.sub(r'^\s*\d+[\.、\s]\s*', '', line).strip()
        if content:
            valid_lines.append(f"{count}.{content}")
            count += 1
    return "\n".join(valid_lines)

def smart_chunk_text(text, max_chars=1200):
    """智能语义拆分，防止段落切在句子中间"""
    chunks = []
    while len(text) > max_chars:
        split_index = -1
        # 优先在句号、感叹号、换行处切割
        for mark in ["\n", "。", "！", "？"]:
            pos = text.rfind(mark, 0, max_chars)
            split_index = max(split_index, pos)
        
        if split_index == -1:
            split_index = max_chars
        else:
            split_index += 1 
            
        chunks.append(text[:split_index].strip())
        text = text[split_index:]
    if text:
        chunks.append(text.strip())
    return [c for c in chunks if c]

# ==========================================
# 2. 页面配置与初始化
# ==========================================

st.set_page_config(page_title="解说分镜 Pro V15", layout="wide")

if 'final_storyboard' not in st.session_state:
    st.session_state.final_storyboard = ""
if 'original_text_clean' not in st.session_state:
    st.session_state.original_text_clean = ""

# --- 侧边栏 ---
with st.sidebar:
    st.title("⚙️ 导演引擎配置")
    api_key = st.text_input("1. API Key", type="password")
    base_url = st.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("3. Model ID", value="gpt-4o")
    st.caption("提示：如果报错 503，请检查上面的 Model ID 是否正确（推荐 gpt-4o）")
    st.divider()
    st.info("💡 V15 协作版：\n1. 支持 7000字+ 长文\n2. 0字损耗校验\n3. 手动编辑后可一键重排序号")

# ==========================================
# 3. 主界面逻辑
# ==========================================

st.title("🎬 电影解说·像素级分镜系统 (V15)")
uploaded_file = st.file_uploader("📂 选择本地文案 TXT 文件", type=['txt'])

if uploaded_file:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    # 锁定原始数据
    st.session_state.original_text_clean = "".join(raw_text.split())
    input_len = len(st.session_state.original_text_clean)

    # 看板
    st.subheader("📊 逻辑稽核面板")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 启动自动化分镜"):
        if not api_key:
            st.error("请先在左侧输入 API Key")
        else:
            try:
                # 规范化 URL
                client = OpenAI(api_key=api_key, base_url=base_url.split('/chat')[0].strip() + "/v1")
                
                # 执行拆分
                chunks = smart_chunk_text(st.session_state.original_text_clean)
                st.write(f"📦 文本已拆分为 {len(chunks)} 个任务块，正在处理...")
                
                all_results = []
                current_idx = 1
                prog = st.progress(0)
                
                for i, chunk in enumerate(chunks):
                    with st.spinner(f"正在处理第 {i+1} 块内容..."):
                        prompt = f"""你是一个解说分镜导演。
1. 1:1 像素级还原原文，不准漏字，不准多字。
2. 每行字数严格在 25-35 字之间，超标必切断。
3. 只要主语切换或台词结束，必须换行。
4. 编号从 {current_idx} 开始。
待处理文本流：
{chunk}"""
                        
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": "你只输出带编号的分镜列表，严禁废话。"},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0
                        )
                        chunk_res = response.choices[0].message.content.strip()
                        all_results.append(chunk_res)
                        
                        # 获取最后序号用于下一块衔接
                        nums = re.findall(r'(\d+)[\.、]', chunk_res)
                        if nums:
                            current_idx = int(nums[-1]) + 1
                        prog.progress((i+1)/len(chunks))
                
                st.session_state.final_storyboard = "\n".join(all_results)
                st.success("AI 分镜处理完毕！")
            except Exception as e:
                st.error(f"处理失败: {str(e)}")

# ==========================================
# 4. 编辑与校准面板
# ==========================================

if st.session_state.final_storyboard:
    st.divider()
    
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.subheader("✍️ 导演精修编辑器")
        # 直接使用组件返回值更新
        edited_text = st.text_area(
            "手动调整内容 (回车增加分镜，删除换行合并)：",
            value=st.session_state.final_storyboard,
            height=600
        )
        
        c1, c2 = st.columns(2)
        if c1.button("🔢 校准所有分镜序号"):
            st.session_state.final_storyboard = reindex_text(edited_text)
            st.rerun()
            
        c2.download_button("💾 下载分镜脚本", st.session_state.final_storyboard, "storyboard.txt")

    with col_r:
        st.subheader("📊 实时节奏监控")
        # 实时字数计算
        current_clean = get_pure_text(st.session_state.final_storyboard)
        curr_len = len(current_clean)
        diff = curr_len - len(st.session_state.original_text_clean)
        
        # 提取分镜行
        shot_lines = [l for l in st.session_state.final_storyboard.split('\n') if re.match(r'^\d+', l.strip())]
        
        st.metric("生成分镜总数", f"{len(shot_lines)} 组")
        st.metric("当前还原字数", f"{curr_len} 字")
        
        if diff == 0:
            st.success("✅ 字数 100% 对齐")
        else:
            st.error(f"❌ 偏差：{diff} 字")
            st.caption("正数为重复/多字，负数为漏字。")

        # 节奏分析表
        analysis = []
        for i, line in enumerate(shot_lines):
            txt = re.sub(r'^\d+[\.、\s]\s*', '', line)
            analysis.append({"镜头": i+1, "字数": len(txt), "状态": "✅" if len(txt) <= 35 else "⚠️过长"})
        
        st.dataframe(pd.DataFrame(analysis), height=400, use_container_width=True)
