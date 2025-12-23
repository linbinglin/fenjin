import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V17 - 镜像分割版", layout="wide")

# --- 工具函数：绝对文字统计（只统计文案，不计编号和符号） ---
def get_clean_content_only(text):
    if not text: return ""
    # 1. 移除形如 "1. ", "123. " 的行首编号
    text = re.sub(r'^\s*\d+[\.．、\s\-]*', '', text, flags=re.MULTILINE)
    # 2. 提取汉字、字母、数字
    content = "".join(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', text))
    return content

def count_pure_text(text):
    return len(get_clean_content_only(text))

# --- 工具函数：强制重新编号 ---
def renumber_by_lines(text_input):
    lines = text_input.split('\n')
    clean_lines = []
    for l in lines:
        # 移除已有的编号
        s = re.sub(r'^\s*\d+[\.．、\s\-]*', '', l).strip()
        if s: clean_lines.append(s)
    
    numbered = "\n".join([f"{i+1}. {c}" for i, c in enumerate(clean_lines)])
    return numbered, clean_lines

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ V17 镜像分割协议")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    st.divider()
    st.markdown("### 🛠️ 工作原理：")
    st.caption("AI 仅负责在文中插入 [BREAK] 标记。Python 负责物理切割。这样能 100% 避免 AI 乱写编号导致的字数偏差。")
    chunk_size = st.slider("处理窗口", 500, 2000, 1000)

# --- 状态管理 ---
if 'v17_script' not in st.session_state: st.session_state.v17_script = ""
if 'v17_list' not in st.session_state: st.session_state.v17_list = []
if 'origin_count' not in st.session_state: st.session_state.origin_count = 0

st.title("🎥 剧情逻辑分镜系统 (V17 镜像分割版)")

# 1. 上传
uploaded_file = st.file_uploader("第一步：上传文案 (TXT)", type=['txt'])
if uploaded_file:
    raw_content = uploaded_file.read().decode("utf-8")
    # 预先清洗：去掉换行和空格得到纯净原文
    clean_origin = "".join(raw_content.split())
    st.session_state.origin_count = count_pure_text(clean_origin)
    
    st.info(f"📄 原始文案净字数：{st.session_state.origin_count} (已排除所有格式干扰)")

    if st.button("🚀 启动镜像分割（零偏差模式）"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            # 物理切片
            chunks = [clean_origin[i:i+chunk_size] for i in range(0, len(clean_origin), chunk_size)]
            all_processed_text = ""
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                # 重新设计的分割 Prompt
                system_prompt = """你是一个文本分割器。
                【任务】：在不改动任何文字的前提下，在逻辑转折处插入 [BREAK] 标记。
                【禁令】：
                1. 严禁改动、删除、添加任何文字。
                2. 严禁输出编号。
                3. 严禁添加描述。
                【输出示例】：
                这是一段文案[BREAK]这是第二段文案[BREAK]这是第三段文案"""
                
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_id,
                        "messages": [{"role": "system", "content": system_prompt},
                                     {"role": "user", "content": f"请处理此段文字：\n{chunk}"}],
                        "temperature": 0.0
                    }
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    # 将 AI 插入的标记转化为换行
                    res = response.json()['choices'][0]['message']['content']
                    all_processed_text += res.replace("[BREAK]", "\n") + "\n"
                except:
                    st.error(f"第 {idx+1} 块异常")
                
                progress.progress((idx+1)/len(chunks))
            
            # 后处理：由 Python 统一打编号，确保编号不计入字数核算
            new_s, new_l = renumber_by_lines(all_processed_text)
            st.session_state.v17_script = new_s
            st.session_state.v17_list = new_l

# --- 2. 交互看板 ---
if st.session_state.v17_script:
    # 核心校准：只对比文案字数
    current_content_count = count_pure_text(st.session_state.v17_script)
    diff = current_content_count - st.session_state.origin_count

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文净字数", st.session_state.origin_count)
    c2.metric("当前分镜组数", len(st.session_state.v17_list))
    c3.metric("分镜净字数", current_content_count)
    
    if diff == 0:
        c4.success("✨ 零偏差：文案完全匹配")
    else:
        c4.error(f"偏差：{diff} 字")
        st.warning(f"检测到偏差！建议点击下方‘一键重编’，系统将尝试重新对齐。")

    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("📝 分镜无损编辑器")
        # 实时同步编辑器的变化
        edited_text = st.text_area("换行即分镜，修改后请点击重编", 
                                   value=st.session_state.v17_script, 
                                   height=600)
        
        if st.button("🔗 自动校准编号与字数", type="primary"):
            new_s, new_l = renumber_by_lines(edited_text)
            st.session_state.v17_script = new_s
            st.session_state.v17_list = new_l
            st.rerun()

    with col_r:
        st.subheader("📊 分镜内容详情")
        df = pd.DataFrame({
            "序号": range(1, len(st.session_state.v17_list) + 1),
            "内容预览": st.session_state.v17_list,
            "净字数": [count_pure_text(s) for s in st.session_state.v17_list]
        })
        st.dataframe(df, height=550, use_container_width=True)
        st.download_button("💾 导出分镜脚本", st.session_state.v17_script, file_name="storyboard_v17.txt")

    if diff != 0:
        with st.expander("🔍 差异深度排查"):
            st.write("以下是分镜中提取的所有纯文字，请对比哪里多出了内容：")
            st.text(get_clean_content_only(st.session_state.v17_script))
