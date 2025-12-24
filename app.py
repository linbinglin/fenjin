import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V21 - 混合驱动版", layout="wide")

# --- 工具函数：绝对文字统计 (极致精准) ---
def get_clean_content_only(text):
    if not text: return ""
    text = re.sub(r'^\s*\d+[\.．、\s\-]*', '', text, flags=re.MULTILINE)
    return "".join(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]', text))

def count_pure_text(text):
    return len(get_clean_content_only(text))

# --- 工具函数：重编序号 ---
def renumber_by_lines(text_input):
    lines = text_input.split('\n')
    # 彻底清洗，只保留有实际内容的行
    clean_lines = [l.strip() for l in lines if re.sub(r'^\s*\d+[\.．、\s\-]*', '', l).strip()]
    numbered = "\n".join([f"{i+1}. {re.sub(r'^\s*\d+[\.．、\s\-]*', '', c).strip()}" for i, c in enumerate(clean_lines)])
    return numbered, [re.sub(r'^\s*\d+[\.．、\s\-]*', '', l).strip() for l in clean_lines]

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ V21 混合驱动配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    st.divider()
    st.markdown("### 🎬 节奏护栏 (Guardrails)")
    soft_limit = st.slider("理想单镜字数 (软限制)", 25, 55, 45)
    hard_limit = st.slider("强制切分上限 (硬限制)", 60, 100, 70)
    st.caption(f"AI 会力求每镜长 {soft_limit} 字，但绝不允许超过 {hard_limit} 字。")
    chunk_size = st.slider("处理窗口", 500, 1500, 1000)

# --- 状态管理 ---
if 'v21_script' not in st.session_state: st.session_state.v21_script = ""
if 'v21_list' not in st.session_state: st.session_state.v21_list = []
if 'origin_count' not in st.session_state: st.session_state.origin_count = 0

st.title("🎥 剧情逻辑分镜系统 (V21 混合驱动版)")

# 1. 上传
uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])
if uploaded_file:
    raw_content = uploaded_file.read().decode("utf-8")
    clean_origin_text = "".join(raw_content.split())
    st.session_state.origin_count = count_pure_text(clean_origin_text)
    
    st.info(f"📄 原始文案净字数：{st.session_state.origin_count} 字")

    if st.button("🚀 启动混合驱动分镜"):
        if not api_key: st.error("请填入 API Key")
        else:
            chunks = [clean_origin_text[i:i+chunk_size] for i in range(0, len(clean_origin_text), chunk_size)]
            all_processed_text = ""
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                # V21 核心 Prompt：混合驱动
                system_prompt = f"""你是一位经验丰富的电影导演，既有艺术感，又有技术纪律。
                【核心任务】：在原文中插入 [切] 标记以完成分镜，确保100%文字无损。
                【节奏准则 - 混合驱动】：
                1. 导演意图：首先根据场景、人物、动作、情绪的自然变化来判断切分点。
                2. 节奏目标 (软限制)：在满足意图的基础上，力求让每个分镜的长度在 {soft_limit} 字左右，以保证流畅的观影节奏。
                3. 强制护栏 (硬限制)：任何一个分镜的长度【绝对不能】超过 {hard_limit} 字。如果一段连续描述过长，必须在最合适的逻辑停顿处（如逗号后）强制插入 [切]。
                【铁律】：严禁输出编号，严禁修改原文。
                """
                
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_id,
                        "messages": [{"role": "system", "content": system_prompt},
                                     {"role": "user", "content": f"请为这段文案进行混合驱动分镜：\n{chunk}"}],
                        "temperature": 0.2
                    }
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    res = response.json()['choices'][0]['message']['content']
                    all_processed_text += res.replace("[切]", "\n") + "\n"
                except Exception as e: st.error(f"处理块 {idx+1} 异常: {e}")
                
                progress.progress((idx+1)/len(chunks))
            
            new_s, new_l = renumber_by_lines(all_processed_text)
            st.session_state.v21_script = new_s
            st.session_state.v21_list = new_l

# --- 2. 交互看板 ---
if 'v21_script' in st.session_state and st.session_state.v21_script:
    current_content_count = count_pure_text(st.session_state.v21_script)
    diff = current_content_count - st.session_state.origin_count

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文净字数", st.session_state.origin_count)
    c2.metric("生成分镜组数", len(st.session_state.v21_list))
    c3.metric("分镜净字数", current_content_count)
    
    # 最终偏差校准
    if diff != 0:
        c4.error(f"偏差：{diff} 字")
        st.warning("检测到微小偏差，可能是由特殊字符引起。请在左侧编辑器手动校准后点击下方重编按钮。")
    else:
        c4.success("✨ 零偏差：完美匹配")

    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.subheader("📝 分镜节奏编辑器")
        edited_text = st.text_area("手动微调后，点击下方按钮校准", value=st.session_state.v21_script, height=600, key="v21_area")
        
        if st.button("🔗 自动校准编号与字数", type="primary"):
            new_s, new_l = renumber_by_lines(edited_text)
            st.session_state.v21_script = new_s
            st.session_state.v21_list = new_l
            st.rerun()

    with col_r:
        st.subheader("📊 视觉节奏监控表")
        df = pd.DataFrame({
            "序号": range(1, len(st.session_state.v21_list) + 1),
            "内容预览": st.session_state.v21_list,
            "净字数": [count_pure_text(s) for s in st.session_state.v21_list]
        })
        
        # 节奏高亮：基于硬限制
        def color_rhythm(val):
            if val > hard_limit: return 'background-color: #ffcccc' # 超出硬限制，红色警报
            if val < 15: return 'background-color: #fff9c4' # 过短，黄色提示
            return ''
        
        st.dataframe(df.style.applymap(color_rhythm, subset=['净字数']), height=550, use_container_width=True)
        st.download_button("💾 导出分镜脚本", st.session_state.v21_script, file_name="storyboard_v21.txt")
