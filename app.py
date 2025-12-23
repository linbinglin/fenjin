import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V13 - 协同专家版", layout="wide")

# --- 工具函数：只统计有效字符（汉字、数字、字母） ---
def count_valid_chars(text):
    if not text: return 0
    # 使用正则匹配所有汉字、字母和数字
    valid_content = re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', text)
    return len(valid_content)

# --- 工具函数：一键重编序号 ---
def renumber_text(raw_text):
    lines = raw_text.split('\n')
    new_shots = []
    count = 1
    for line in lines:
        # 去掉每行开头的旧数字序号标记（支持 1. 1、 1 ）
        clean_line = re.sub(r'^\d+[.、\s]*', '', line).strip()
        if clean_line: # 确保不是空行
            new_shots.append(f"{count}. {clean_line}")
            count += 1
    return "\n".join(new_shots), [re.sub(r'^\d+[.、\s]*', '', l).strip() for l in lines if re.sub(r'^\d+[.、\s]*', '', l).strip()]

# --- 侧边栏 ---
with st.sidebar:
    st.header("🎬 导演引擎控制台")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    st.divider()
    st.markdown("### 🎭 分镜准则：\n1. 剧情驱动\n2. 动作闭环\n3. 对话独立\n4. 节奏参考 (30-45字)")
    chunk_val = st.slider("处理窗口大小", 500, 3000, 1500)

# --- 初始化 Session State ---
if 'final_script' not in st.session_state:
    st.session_state.final_script = ""  # 存储带序号的文本
if 'pure_shots_list' not in st.session_state:
    st.session_state.pure_shots_list = [] # 存储不带序号的纯列表
if 'raw_word_count' not in st.session_state:
    st.session_state.raw_word_count = 0

st.title("🎥 剧情逻辑分镜系统 (V13 协同版)")

# 1. 文件上传
uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])
if uploaded_file:
    raw_content = uploaded_file.read().decode("utf-8")
    # 去除干扰符号进行预分析
    clean_text = "".join(raw_content.split())
    st.session_state.raw_word_count = count_valid_chars(clean_text)
    
    col_info, col_btn = st.columns([3, 1])
    col_info.info(f"📄 文本解析成功 | 纯文字总数：{st.session_state.raw_word_count}")
    
    if col_btn.button("🚀 开始 AI 逻辑分镜"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            chunks = [clean_text[i:i+chunk_val] for i in range(0, len(clean_text), chunk_val)]
            all_lines = []
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                system_prompt = "你是一位资深解说导演。请将文本【无损】还原为逻辑分镜。每镜20-45字，场景或动作切换必换镜。严禁删改字词。仅输出带编号的结果。"
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {"model": model_id, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": chunk}], "temperature": 0.2}
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    res = response.json()['choices'][0]['message']['content']
                    lines = re.findall(r'\d+[.、\s]+(.*)', res)
                    all_lines.extend([l.strip() for l in lines if l.strip()])
                except: pass
                progress.progress((idx + 1) / len(chunks))
            
            # 更新状态
            st.session_state.pure_shots_list = all_lines
            st.session_state.final_script = "\n".join([f"{i+1}. {s}" for i, s in enumerate(all_lines)])

# --- 2. 核心编辑与稽核区 ---
if st.session_state.final_script:
    # 实时计算当前编辑器的字数
    current_edit_content = st.session_state.final_script
    processed_valid_count = count_valid_chars(current_edit_content)
    diff = processed_valid_count - st.session_state.raw_word_count

    st.divider()
    # 稽核面板
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文文字数", st.session_state.raw_word_count)
    c2.metric("当前分镜组数", len(st.session_state.pure_shots_list))
    c3.metric("处理后文字数", processed_valid_count)
    c4.metric("偏差值 (纯字数)", f"{diff} 字", delta=diff, delta_color="inverse" if diff != 0 else "normal")

    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("📝 分镜正文预览 (可直接修改)")
        # 用户在文本框内进行修改
        edited_text = st.text_area("手动微调区：你可以删除序号、合并行、拆分行后再点击下方重编", 
                                   value=st.session_state.final_script, 
                                   height=500,
                                   key="main_editor")
        
        # 功能：一键自动添加数字序号
        if st.button("🔢 一键重编数字序号"):
            new_script, new_list = renumber_text(edited_text)
            st.session_state.final_script = new_script
            st.session_state.pure_shots_list = new_list
            st.rerun() # 强制刷新页面显示新序号

    with col_right:
        st.subheader("📊 视觉节奏监控")
        # 实时同步表格
        df = pd.DataFrame({
            "序号": range(1, len(st.session_state.pure_shots_list) + 1),
            "内容": st.session_state.pure_shots_list,
            "文字数": [count_valid_chars(s) for s in st.session_state.pure_shots_list]
        })
        def rhythm_tag(l):
            return "✅ 标准" if 15 <= l <= 45 else ("⚡ 快节奏" if l < 15 else "🐢 慢镜头")
        df["节奏建议"] = df["文字数"].apply(rhythm_tag)
        st.dataframe(df, height=450, use_container_width=True)
        
        st.download_button("💾 导出最终分镜稿", st.session_state.final_script, file_name="final_storyboard.txt")

    st.caption("提示：在左侧编辑器手动删减或合并后，点击‘一键重编数字序号’即可自动对齐所有编号。")
