import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V20 - 意图驱动版", layout="wide")

# --- 工具函数：绝对文字统计 (极致精准，只计中英数字) ---
def get_clean_content_only(text):
    if not text: return ""
    text = re.sub(r'^\s*\d+[\.．、\s\-]*', '', text, flags=re.MULTILINE) # 移除行首编号
    # 提取所有中文字符、英文字母、数字
    return "".join(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', text))

def count_pure_text(text):
    return len(get_clean_content_only(text))

# --- 工具函数：重编序号 ---
def renumber_by_lines(text_input):
    lines = text_input.split('\n')
    clean_lines = [get_clean_content_only(l) for l in lines if get_clean_content_only(l)] # 确保只有纯文字才算一行
    numbered = "\n".join([f"{i+1}. {c}" for i, c in enumerate(clean_lines)])
    return numbered, clean_lines

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ V20 意图驱动配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    st.divider()
    st.markdown("### 🎬 导演视角：分镜目的")
    st.caption("AI 将以【提升观影体验】为核心，根据场景、人物、动作、情绪的自然变化来判断分镜。")
    chunk_size = st.slider("处理窗口", 500, 1500, 1000)

# --- 状态管理 ---
if 'v20_script' not in st.session_state: st.session_state.v20_script = ""
if 'v20_list' not in st.session_state: st.session_state.v20_list = []
if 'origin_count' not in st.session_state: st.session_state.origin_count = 0

st.title("🎥 剧情逻辑分镜系统 (V20 意图驱动版)")

# 1. 上传
uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])
if uploaded_file:
    raw_content = uploaded_file.read().decode("utf-8")
    clean_origin_text = "".join(raw_content.split())
    st.session_state.origin_count = count_pure_text(clean_origin_text)
    
    st.info(f"📄 原始文案净字数：{st.session_state.origin_count} 字")

    if st.button("🚀 启动意图驱动分镜"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            chunks = [clean_origin_text[i:i+chunk_size] for i in range(0, len(clean_origin_text), chunk_size)]
            all_processed_text = ""
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                # V20 核心 Prompt：强调导演意图
                system_prompt = """你是一位顶级的电影导演和剪辑师。你的任务是根据一段剧本文案，为其规划出最能打动观众的分镜。
                【分镜目的】：
                1. 提升观影体验：确保每个分镜都是一个有明确视觉焦点的画面，能流畅衔接。
                2. 突出核心信息：通过分镜切换，强调关键对话、动作或情绪变化。
                3. 节奏自然：根据剧情的快慢、情感的起伏，自然地调整分镜的长度，不必拘泥于固定字数。
                【分镜依据】：
                - 场景的转换、人物的进出、核心动作的完成、对话的切换、情绪的重大转折，是主要切分点。
                - 短促的动作、连贯的心理描写、同一个场景的细节，应尽量合并，避免画面过于跳跃。
                【铁律】：
                - 100% 原文：严禁删除、修改、添加任何原文文字。
                - 严禁输出编号，只输出带有 [切] 标记的长文本。
                """
                
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_id,
                        "messages": [{"role": "system", "content": system_prompt},
                                     {"role": "user", "content": f"请以导演的视角，为这段文案插入 [切] 标记以完成分镜：\n{chunk}"}],
                        "temperature": 0.3 # 略微提升温度，让 AI 更“聪明”地找切分点
                    }
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    res = response.json()['choices'][0]['message']['content']
                    all_processed_text += res.replace("[切]", "\n") + "\n"
                except Exception as e:
                    st.error(f"处理第 {idx+1} 块异常: {e}")
                
                progress.progress((idx+1)/len(chunks))
            
            new_s, new_l = renumber_by_lines(all_processed_text)
            st.session_state.v20_script = new_s
            st.session_state.v20_list = new_l

# --- 2. 交互看板 ---
if 'v20_script' in st.session_state and st.session_state.v20_script:
    current_content_count = count_pure_text(st.session_state.v20_script)
    diff = current_content_count - st.session_state.origin_count

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文净字数", st.session_state.origin_count)
    c2.metric("生成分镜组数", len(st.session_state.v20_list))
    c3.metric("分镜净字数", current_content_count)
    
    if diff == 0:
        c4.success("✨ 零偏差：完美匹配")
    else:
        c4.error(f"偏差：{diff} 字")

    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("📝 分镜意图编辑器")
        st.caption("手动微调：根据你的导演直觉调整分镜。修改后点击下方按钮校准。")
        edited_text = st.text_area("编辑区", value=st.session_state.v20_script, height=600, key="v20_area")
        
        if st.button("🔗 自动校准编号与字数", type="primary"):
            new_s, new_l = renumber_by_lines(edited_text)
            st.session_state.v20_script = new_s
            st.session_state.v20_list = new_l
            st.rerun()

    with col_r:
        st.subheader("📊 视觉节奏监控表")
        df = pd.DataFrame({
            "序号": range(1, len(st.session_state.v20_list) + 1),
            "内容预览": st.session_state.v20_list,
            "净字数": [count_pure_text(s) for s in st.session_state.v20_list]
        })
        
        # 节奏高亮：太短和太长都提醒，但不再强制
        def color_rhythm(val):
            if val > 60: return 'background-color: #ffcccc' # 超过60字太长
            if val < 10: return 'background-color: #fff9c4' # 少于10字太短
            return ''
        
        st.dataframe(df.style.applymap(color_rhythm, subset=['净字数']), height=550, use_container_width=True)
        st.download_button("💾 导出分镜脚本", st.session_state.v20_script, file_name="storyboard_v20.txt")
