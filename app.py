import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V14 - 智能排版版", layout="wide")

# --- 工具函数：只统计有效字符（汉字、数字、字母） ---
def count_valid_chars(text):
    if not text: return 0
    # 匹配所有汉字、字母和数字，排除标点符号、空格和换行
    valid_content = re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', text)
    return len(valid_content)

# --- 核心函数：强制根据“分段”重新编号 ---
def force_renumber_by_paragraphs(text_input):
    # 1. 按行切分（物理分段）
    raw_lines = text_input.split('\n')
    
    clean_shots = []
    for line in raw_lines:
        # 2. 去掉每行开头可能存在的数字编号（如 1. 1、 1- 等）
        # 匹配开头是数字且跟着标点符号或空格的情况
        stripped_line = re.sub(r'^\s*\d+[\.．、\s\-]*', '', line).strip()
        
        # 3. 如果这一行有内容，就保留
        if stripped_line:
            clean_shots.append(stripped_line)
    
    # 4. 重新组合：打上崭新的序号
    numbered_script = "\n".join([f"{i+1}. {content}" for i, content in enumerate(clean_shots)])
    return numbered_script, clean_shots

# --- 侧边栏 ---
with st.sidebar:
    st.header("🎬 导演引擎控制台")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    st.divider()
    st.markdown("### 🎭 分镜准则：\n1. 剧情驱动 (意群分镜)\n2. 动作闭环\n3. 物理分段即分镜\n4. 偏差值监控（不计标点）")
    chunk_val = st.slider("处理窗口大小", 500, 3000, 1500)

# --- 初始化 Session State ---
if 'final_script' not in st.session_state:
    st.session_state.final_script = ""  # 带序号的全文
if 'pure_shots_list' not in st.session_state:
    st.session_state.pure_shots_list = [] # 纯文字列表
if 'raw_word_count' not in st.session_state:
    st.session_state.raw_word_count = 0

st.title("🎥 剧情逻辑分镜系统 (V14 智能排版)")

# 1. 文件上传
uploaded_file = st.file_uploader("第一步：上传文案 (TXT)", type=['txt'])
if uploaded_file:
    raw_content = uploaded_file.read().decode("utf-8")
    # 彻底清除换行空格，得到纯净文字流
    clean_text_flow = "".join(raw_content.split())
    st.session_state.raw_word_count = count_valid_chars(clean_text_flow)
    
    col_info, col_btn = st.columns([3, 1])
    col_info.info(f"📄 文本分析成功 | 原始文字净数量：{st.session_state.raw_word_count}")
    
    if col_btn.button("🚀 开始 AI 逻辑分析生成"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            # 分片逻辑保持稳定，防止长文案压缩
            chunks = [clean_text_flow[i:i+chunk_val] for i in range(0, len(clean_text_flow), chunk_val)]
            all_lines = []
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                system_prompt = "你是一位电影导演。将以下文本流【无损】转化为分镜，每镜包含完整动作或情节，25-45字左右。物理换行输出。严禁改动原文。"
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {"model": model_id, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": chunk}], "temperature": 0.2}
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    res = response.json()['choices'][0]['message']['content']
                    # 兼容性提取：提取带数字或不带数字的行
                    lines = [re.sub(r'^\s*\d+[\.．、\s\-]*', '', l).strip() for l in res.split('\n') if l.strip()]
                    all_lines.extend(lines)
                except: pass
                progress.progress((idx + 1) / len(chunks))
            
            st.session_state.pure_shots_list = all_lines
            st.session_state.final_script = "\n".join([f"{i+1}. {s}" for i, s in enumerate(all_lines)])

# --- 2. 核心编辑与稽核区 ---
if st.session_state.final_script:
    # 稽核计算（实时）
    current_script = st.session_state.final_script
    processed_word_count = count_valid_chars(current_script)
    diff = processed_word_count - st.session_state.raw_word_count

    st.divider()
    # 顶部指标卡
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文文字数", st.session_state.raw_word_count)
    m2.metric("当前分镜组数", len(st.session_state.pure_shots_list))
    m3.metric("分镜文字数", processed_word_count)
    m4.metric("偏差值 (不计标点)", f"{diff} 字", delta=diff, delta_color="inverse" if diff != 0 else "normal")

    col_l, col_r = st.columns([1, 1])
    
    with col_l:
        st.subheader("📝 分镜无损编辑器")
        st.caption("【操作指南】在下方直接修改文字，若想分出一组新分镜，直接按“回车键”换行即可。修改完点下方蓝色按钮。")
        
        # 使用 key 绑定 session_state
        user_edited_text = st.text_area("编辑器内容", 
                                        value=st.session_state.final_script, 
                                        height=600, 
                                        key="editor_input")
        
        # 重点：点击后根据“物理换行”重新排布所有序号
        if st.button("🔗 按照分段：一键自动重编序号", type="primary"):
            new_script, new_list = force_renumber_by_paragraphs(user_edited_text)
            st.session_state.final_script = new_script
            st.session_state.pure_shots_list = new_list
            st.rerun() # 立即刷新，让用户看到 1. 2. 3. 重新排列后的结果

    with col_r:
        st.subheader("📊 实时视觉节奏分析")
        df = pd.DataFrame({
            "分镜序号": range(1, len(st.session_state.pure_shots_list) + 1),
            "内容预览": st.session_state.pure_shots_list,
            "有效字数": [count_valid_chars(s) for s in st.session_state.pure_shots_list]
        })
        def get_status(l):
            if l < 10: return "⚡ 快节奏"
            if 10 <= l <= 45: return "✅ 标准"
            return "🐢 慢/需拆分"
        df["节奏建议"] = df["有效字数"].apply(get_status)
        st.dataframe(df, height=550, use_container_width=True)
        
        st.download_button("💾 下载脚本", st.session_state.final_script, file_name="storyboard_final.txt")

    st.warning("⚠️ 提示：手动微调后，请务必点击【一键自动重编序号】以更新右侧分析报表及偏差值。")



