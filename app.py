import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V16 - 零增减版", layout="wide")

# --- 工具函数：只统计有效文字（剔除所有非文案字符） ---
def get_pure_text(text):
    if not text: return ""
    # 提取汉字、字母、数字（剔除标点、空格、序号）
    return "".join(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', text))

def count_chars(text):
    return len(get_pure_text(text))

# --- 核心函数：强制分段并重新编号 ---
def force_renumber_v16(text_input):
    # 先按换行符拆分
    lines = text_input.split('\n')
    clean_shots = []
    for line in lines:
        # 移除行首的数字序号、点、空格
        s = re.sub(r'^\s*\d+[\.．、\s\-]*', '', line).strip()
        if s:
            clean_shots.append(s)
    # 重新打标
    new_script = "\n".join([f"{i+1}. {c}" for i, c in enumerate(clean_shots)])
    return new_script, clean_shots

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ V16 零增减协议")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    st.divider()
    st.warning("⚠️ V16 核心逻辑：AI 被降维为‘回车插入工具’，严禁任何文学发挥。")
    chunk_size = st.slider("处理窗口（建议 1000）", 500, 2000, 1000)

# --- 状态初始化 ---
if 'v16_script' not in st.session_state: st.session_state.v16_script = ""
if 'v16_list' not in st.session_state: st.session_state.v16_list = []
if 'source_pure_count' not in st.session_state: st.session_state.source_pure_count = 0

st.title("🎥 剧情逻辑分镜系统 (V16 零增减复刻版)")

# 1. 上传文件
uploaded_file = st.file_uploader("第一步：上传文案 (TXT)", type=['txt'])
if uploaded_file:
    raw_content = uploaded_file.read().decode("utf-8")
    # 彻底清洗原文：去除换行、空格、标点，得到最纯净的字数基准
    source_pure = get_pure_text(raw_content)
    st.session_state.source_pure_count = len(source_pure)
    
    st.info(f"📄 原始文字基准：{st.session_state.source_pure_count} 字 (已排除标点、空格、格式符)")

    if st.button("🚀 启动零增减分镜（强制复刻模式）"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            # 采用严格不重叠切片
            full_text = "".join(raw_content.split())
            chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
            
            all_lines = []
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                # 重新设计的 Prompt：重点在于“不允许添加任何描述”
                system_prompt = """你是一个分镜排版机器。
                【任务】：在不改动、不增加、不减少任何文字的前提下，根据剧情转折、动作切换插入换行。
                【禁令】：
                1. 禁止添加“画面：”、“场景：”、“Action”等任何解释性文字。
                2. 禁止对原文进行润色。
                3. 禁止重复输出。
                【格式】：每镜独立一行，每行开头必须带数字编号。"""
                
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_id,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请将以下文本进行分镜排版（保持文字完全一致）：\n{chunk}"}
                        ],
                        "temperature": 0.0
                    }
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    res_text = response.json()['choices'][0]['message']['content']
                    
                    # 提取内容
                    lines = [re.sub(r'^\s*\d+[\.．、\s\-]*', '', l).strip() for l in res_text.split('\n') if l.strip()]
                    all_lines.extend(lines)
                except:
                    st.error(f"第 {idx+1} 块处理异常")
                
                progress.progress((idx + 1) / len(chunks))
            
            # 保存结果
            st.session_state.v16_list = all_lines
            st.session_state.v16_script = "\n".join([f"{i+1}. {s}" for i, s in enumerate(all_lines)])

# --- 2. 交互编辑区 ---
if st.session_state.v16_script:
    # 稽核：只对比纯文字
    current_pure_count = count_chars(st.session_state.v16_script)
    diff = current_pure_count - st.session_state.source_pure_count
    
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文基准字数", st.session_state.source_pure_count)
    c2.metric("当前分镜组数", len(st.session_state.v16_list))
    c3.metric("生成纯字数", current_pure_count)
    
    # 偏差值处理：偏差超过0即变红
    if diff != 0:
        c4.error(f"偏差：{diff} 字")
        if diff > 0:
            st.warning(f"⚠️ 警告：多了 {diff} 个字。可能是 AI 自行添加了描述语或产生了重复。请检查右侧列表。")
        else:
            st.error(f"⚠️ 警告：少了 {abs(diff)} 个字。AI 偷懒删减了内容。")
    else:
        c4.success("✨ 零偏差：完美复刻")

    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("📝 分镜无损编辑器")
        edited_text = st.text_area("编辑区：换行即分镜", value=st.session_state.v16_script, height=600, key="editor_v16")
        
        if st.button("🔗 一键重新排列序号并校验", type="primary"):
            new_s, new_l = force_renumber_v16(edited_text)
            st.session_state.v16_script = new_s
            st.session_state.v16_list = new_l
            st.rerun()

    with col_r:
        st.subheader("📊 实时节奏分析表")
        df = pd.DataFrame({
            "序号": range(1, len(st.session_state.v16_list) + 1),
            "内容": st.session_state.v16_list,
            "字数": [count_chars(s) for s in st.session_state.v16_list]
        })
        st.dataframe(df, height=550, use_container_width=True)
        st.download_button("💾 导出最终稿", st.session_state.v16_script, file_name="storyboard_v16.txt")

    # 底部快捷排查
    if diff != 0:
        with st.expander("🔍 点击排查文字差异"):
            st.write("如果字数不符，请对比此处的纯文本流是否包含非原文内容：")
            st.text(get_pure_text(st.session_state.v16_script))
