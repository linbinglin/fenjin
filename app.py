import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V18 - 视觉节奏版", layout="wide")

# --- 工具函数：绝对文字统计 ---
def get_clean_content_only(text):
    if not text: return ""
    # 移除行首编号
    text = re.sub(r'^\s*\d+[\.．、\s\-]*', '', text, flags=re.MULTILINE)
    # 提取有效字符
    return "".join(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', text))

def count_pure_text(text):
    return len(get_clean_content_only(text))

# --- 工具函数：重编序号 ---
def renumber_by_lines(text_input):
    lines = text_input.split('\n')
    clean_lines = [re.sub(r'^\s*\d+[\.．、\s\-]*', '', l).strip() for l in lines if l.strip()]
    numbered = "\n".join([f"{i+1}. {c}" for i, c in enumerate(clean_lines)])
    return numbered, clean_lines

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ V18 视觉节奏配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    st.divider()
    st.markdown("### 🎞️ 节奏准则：")
    target_len = st.number_input("目标单镜字数 (5秒/35字)", value=35)
    st.caption("AI 将在 35 字左右寻找剧情逻辑点进行强行切分，确保视觉不疲劳。")
    chunk_size = st.slider("处理窗口", 500, 1500, 800)

# --- 状态管理 ---
if 'v18_script' not in st.session_state: st.session_state.v18_script = ""
if 'v18_list' not in st.session_state: st.session_state.v18_list = []
if 'origin_count' not in st.session_state: st.session_state.origin_count = 0

st.title("🎥 剧情逻辑分镜系统 (V18 视觉节奏版)")

# 1. 上传
uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])
if uploaded_file:
    raw_content = uploaded_file.read().decode("utf-8")
    clean_origin = "".join(raw_content.split())
    st.session_state.origin_count = count_pure_text(clean_origin)
    
    st.info(f"📄 原始文案净字数：{st.session_state.origin_count} 字")

    if st.button("🚀 启动高频节奏分镜"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            chunks = [clean_origin[i:i+chunk_size] for i in range(0, len(clean_origin), chunk_size)]
            all_processed_text = ""
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                # 重新设计的“节奏导演”Prompt
                system_prompt = f"""你是一位拥有极强视觉节奏感的电影导演。
                【核心任务】：在原文中插入 [切] 标记。
                【分镜要求】：
                1. 节奏控制：平均每 {target_len} 个字必须寻找逻辑点切分一次。单镜严禁超过 60 字。
                2. 逻辑点选择：动作完成、人称切换、环境描写转对话、新信息出现。
                3. 100% 原文：绝对禁止改动、缩写、添加任何原文以外的字词。
                4. 严禁输出编号，只输出带 [切] 标记的长文本。
                """
                
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_id,
                        "messages": [{"role": "system", "content": system_prompt},
                                     {"role": "user", "content": f"请对这段文字进行高频视觉切分：\n{chunk}"}],
                        "temperature": 0.2 # 适度增加灵活性，让它找切分点更聪明
                    }
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    res = response.json()['choices'][0]['message']['content']
                    # 处理 AI 可能输出的冗余描述，只取包含原文的部分
                    all_processed_text += res.replace("[切]", "\n") + "\n"
                except:
                    st.error(f"处理第 {idx+1} 块时异常")
                
                progress.progress((idx+1)/len(chunks))
            
            new_s, new_l = renumber_by_lines(all_processed_text)
            st.session_state.v18_script = new_s
            st.session_state.v18_list = new_l

# --- 2. 交互看板 ---
if st.session_state.v18_script:
    current_content_count = count_pure_text(st.session_state.v18_script)
    diff = current_content_count - st.session_state.origin_count

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文净字数", st.session_state.origin_count)
    c2.metric("生成分镜组数", len(st.session_state.v18_list))
    c3.metric("分镜净字数", current_content_count)
    
    if diff == 0:
        c4.success("✨ 零偏差：文案完全匹配")
    else:
        c4.error(f"偏差：{diff} 字")

    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("📝 分镜节奏编辑器")
        st.caption("提示：若某一段落太长，请手动按‘回车’切分，再点击下方‘一键重编’。")
        edited_text = st.text_area("编辑区", value=st.session_state.v18_script, height=600)
        
        if st.button("🔗 一键校准编号并刷新统计", type="primary"):
            new_s, new_l = renumber_by_lines(edited_text)
            st.session_state.v18_script = new_s
            st.session_state.v18_list = new_l
            st.rerun()

    with col_r:
        st.subheader("📊 视觉节奏监控表")
        df = pd.DataFrame({
            "序号": range(1, len(st.session_state.v18_list) + 1),
            "内容": st.session_state.v18_list,
            "字数": [count_pure_text(s) for s in st.session_state.v18_list]
        })
        
        # 节奏高亮逻辑
        def color_rhythm(val):
            if val > 50: return 'background-color: #ffcccc' # 太长变红
            if val < 15: return 'background-color: #e1f5fe' # 太短变蓝
            return ''
        
        st.dataframe(df.style.applymap(color_rhythm, subset=['字数']), height=550, use_container_width=True)
        st.download_button("💾 导出分镜脚本", st.session_state.v18_script, file_name="storyboard_v18.txt")
