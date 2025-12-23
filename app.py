import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V15 - 极端无损版", layout="wide")

# --- 工具函数：只统计有效字符（排除格式字符） ---
def count_valid_chars(text):
    if not text: return 0
    # 只统计汉字、字母、数字
    valid_content = re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', text)
    return len(valid_content)

# --- 核心函数：根据换行重新编号 ---
def force_renumber_by_paragraphs(text_input):
    raw_lines = text_input.split('\n')
    clean_shots = []
    for line in raw_lines:
        stripped_line = re.sub(r'^\s*\d+[\.．、\s\-]*', '', line).strip()
        if stripped_line:
            clean_shots.append(stripped_line)
    numbered_script = "\n".join([f"{i+1}. {content}" for i, content in enumerate(clean_shots)])
    return numbered_script, clean_shots

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 极端无损协议配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    st.divider()
    st.error("🚨 极端模式提示：\n1. AI 将被禁止任何总结行为。\n2. 若字数仍有偏差，请调小‘处理窗口’。")
    chunk_val = st.slider("处理窗口大小 (字数)", 300, 1500, 800) # 调小窗口能有效防止丢字
    overlap_val = st.slider("切片重叠字数", 0, 100, 50)

# --- 初始化 Session State ---
if 'final_script' not in st.session_state: st.session_state.final_script = ""
if 'pure_shots_list' not in st.session_state: st.session_state.pure_shots_list = []
if 'raw_word_count' not in st.session_state: st.session_state.raw_word_count = 0

st.title("🎥 剧情逻辑分镜系统 (V15 极端无损版)")

# 1. 文件上传
uploaded_file = st.file_uploader("第一步：上传文案 (TXT)", type=['txt'])
if uploaded_file:
    raw_content = uploaded_file.read().decode("utf-8")
    clean_text_flow = "".join(raw_content.split())
    st.session_state.raw_word_count = count_valid_chars(clean_text_flow)
    
    col_info, col_btn = st.columns([3, 1])
    col_info.info(f"📄 原始文字净数量：{st.session_state.raw_word_count} 字")
    
    if col_btn.button("🚀 启动极端无损分镜分析"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            # 使用带重叠的切片逻辑
            chunks = []
            for i in range(0, len(clean_text_flow), chunk_val - overlap_val):
                chunks.append(clean_text_flow[i : i + chunk_val])
            
            all_lines = []
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                # 极端 Prompt 升级：使用了“听写员”比喻
                system_prompt = f"""你是一个极其死板的听写员和分镜师。
                任务：将文本分镜化。
                【铁律】：
                1. 严禁改动、删除、总结、缩减任何一个字！
                2. 必须包含原文中的每一个汉字、每一个数字。
                3. 如果你敢丢掉一个片段，我的项目就会彻底失败。
                4. 逻辑切换：根据场景变化、人称切换、动作连贯性进行物理换行。
                5. 格式：
                   1. 内容...
                   2. 内容...
                请开始分镜，确保输出内容的字数与输入文本完全一致："""
                
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_id, 
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"这是第{idx+1}部分待处理文本，请无损转化：\n{chunk}"}
                        ], 
                        "temperature": 0.0 # 强制 0 随机性，降低自由发挥空间
                    }
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    res = response.json()['choices'][0]['message']['content']
                    
                    # 提取行，并过滤掉因为“重叠切片”可能导致的重复行（简单逻辑处理）
                    lines = [re.sub(r'^\s*\d+[\.．、\s\-]*', '', l).strip() for l in res.split('\n') if l.strip()]
                    
                    # 避免重叠部分的简单去重逻辑：如果新段落的第一行已经在 list 的最后一行出现了，就跳过
                    for line in lines:
                        if not all_lines or line not in all_lines[-2:]: # 简单对比最后两行，防止由于切片重叠导致的重复
                            all_lines.append(line)
                            
                except Exception as e:
                    st.error(f"处理第{idx+1}块时出错")
                
                progress.progress((idx + 1) / len(chunks))
            
            st.session_state.pure_shots_list = all_lines
            st.session_state.final_script = "\n".join([f"{i+1}. {s}" for i, s in enumerate(all_lines)])

# --- 2. 核心编辑与稽核区 ---
if st.session_state.final_script:
    processed_word_count = count_valid_chars(st.session_state.final_script)
    diff = processed_word_count - st.session_state.raw_word_count

    st.divider()
    # 稽核面板：增加颜色警报
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", st.session_state.raw_word_count)
    m2.metric("当前分镜组数", len(st.session_state.pure_shots_list))
    m3.metric("分镜总字数", processed_word_count)
    
    # 偏差值红色预警
    if abs(diff) > 20:
        m4.subheader(f"❌ 偏差：{diff} 字")
        st.error(f"⚠️ 警告：目前丢失了 {abs(diff)} 个字！AI 依然存在删减行为。请尝试调小侧边栏的‘处理窗口大小’到 500 左右并重新生成。")
    else:
        m4.metric("偏差值 (无损度)", f"{diff} 字", delta=diff)

    col_l, col_r = st.columns([1, 1])
    
    with col_l:
        st.subheader("📝 分镜无损编辑器")
        user_edited_text = st.text_area("在下方修改或增加回车：", 
                                        value=st.session_state.final_script, 
                                        height=600, 
                                        key="editor_v15")
        
        if st.button("🔗 确认修改并自动重编序号", type="primary"):
            new_script, new_list = force_renumber_by_paragraphs(user_edited_text)
            st.session_state.final_script = new_script
            st.session_state.pure_shots_list = new_list
            st.rerun()

    with col_r:
        st.subheader("📊 实时视觉节奏分析")
        df = pd.DataFrame({
            "序号": range(1, len(st.session_state.pure_shots_list) + 1),
            "内容": st.session_state.pure_shots_list,
            "字数": [count_valid_chars(s) for s in st.session_state.pure_shots_list]
        })
        st.dataframe(df, height=550, use_container_width=True)
        st.download_button("💾 下载最终脚本", st.session_state.final_script, file_name="storyboard_v15.txt")
