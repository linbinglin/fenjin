import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V11 - 视觉无损分镜", layout="wide")

# 自定义 CSS 提升 UI 质感
st.markdown("""
    <style>
    .metric-box { border: 1px solid #e6e9ef; padding: 15px; border-radius: 10px; background-color: #f8f9fa; }
    .stDataFrame { border: 1px solid #e6e9ef; }
    </style>
""", unsafe_allow_html=True)

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 导演引擎配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    
    st.divider()
    st.markdown("""
    ### 🎬 V11 视觉切分准则：
    1. **主语即镜头**：人称切换（如“我”转“他”）必须断开。
    2. **动作即分镜**：一个核心动作完成后必须切换。
    3. **对话独立性**：台词结束后动作描写严禁混在一起。
    4. **硬性 35 字**：单行依然禁止超过 35 字。
    """)
    max_chars = st.slider("硬性单镜字数限制", 10, 50, 35)

# --- 主界面 ---
st.title("📊 视觉逻辑稽核面板")

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

# 初始化 Session State
if 'final_shots' not in st.session_state:
    st.session_state.final_shots = []
if 'raw_word_count' not in st.session_state:
    st.session_state.raw_word_count = 0

# --- 1. 上传逻辑 ---
uploaded_file = st.file_uploader("选择本地 TXT 文件", type=['txt'])

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    # 彻底去除段落，形成纯文字流
    clean_text = "".join(content.split())
    st.session_state.raw_word_count = len(clean_text)
    
    with st.expander("👁️ 预览待处理文本流"):
        st.write(clean_text)

    if st.button("🚀 启动视觉无损分镜"):
        if not api_key:
            st.error("请先输入 API Key")
        else:
            # 策略：为了防止 7000 字长文被 AI 压缩，我们分段请求（每段约 800 字）
            chunk_size = 800
            chunks = [clean_text[i:i+chunk_size] for i in range(0, len(clean_text), chunk_size)]
            
            all_processed_shots = []
            progress_bar = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                st.write(f"正在处理第 {idx+1}/{len(chunks)} 块数据...")
                
                system_prompt = f"""你是一个好莱坞级别的电影分镜师。你的任务是将文本流【无损】转化为分镜脚本。
                
                硬性准则：
                1. 严禁改动、删除、总结任何原文。输出的所有汉字必须与原文完全一致且顺序相同。
                2. 逻辑分镜点（必须另起一行编号）：
                   - 场景变化时。
                   - 主语/角色切换时。
                   - 动作发生转折或完成时。
                   - 对话开始或结束时。
                3. 每行长度限制：绝对不能超过 {max_chars} 个字。若原文一句话太长，请在语义停顿处强制切分。
                4. 纯净输出：仅输出带有编号的分镜内容，严禁任何废话。
                """
                
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_id,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文本流进行视觉切分：\n{chunk}"}
                        ],
                        "temperature": 0.1 # 极低随机性确保稳定性
                    }
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    chunk_result = response.json()['choices'][0]['message']['content']
                    
                    # 提取编号后的内容
                    lines = re.findall(r'\d+[.、\s]+(.*)', chunk_result)
                    all_processed_shots.extend(lines)
                    
                except Exception as e:
                    st.error(f"处理块 {idx} 时出错: {str(e)}")
                
                progress_bar.progress((idx + 1) / len(chunks))
            
            st.session_state.final_shots = all_processed_shots

# --- 2. 结果展示与稽核 ---
if st.session_state.final_shots:
    processed_text = "".join(st.session_state.final_shots)
    processed_word_count = len(processed_text)
    diff = processed_word_count - st.session_state.raw_word_count
    
    # 更新顶部数据面板
    col_m1.metric("原文总字数", f"{st.session_state.raw_word_count} 字")
    col_m2.metric("生成分镜总数", f"{len(st.session_state.final_shots)} 组")
    col_m3.metric("处理后总字数", f"{processed_word_count} 字")
    col_m4.metric("偏差值", f"{diff} 字", delta=diff, delta_color="inverse")

    st.divider()
    
    c_left, c_right = st.columns([1, 1])
    
    with c_left:
        st.subheader("🎬 视觉分镜编辑器 (无损还原)")
        shot_content = ""
        for i, shot in enumerate(st.session_state.final_shots):
            shot_content += f"{i+1}. {shot}\n"
        st.text_area("分镜正文", shot_content, height=600)

    with c_right:
        st.subheader("📊 实时视觉节奏分析")
        df = pd.DataFrame({
            "序号": range(1, len(st.session_state.final_shots) + 1),
            "内容预览": st.session_state.final_shots,
            "长度": [len(s) for s in st.session_state.final_shots],
            "状态": ["✅ 理想" if len(s) <= max_chars else "⚠️ 偏长" for s in st.session_state.final_shots]
        })
        st.dataframe(df, height=600, use_container_width=True)
        
        avg_len = sum(len(s) for s in st.session_state.final_shots) / len(st.session_state.final_shots)
        st.info(f"💡 平均每镜停留：{avg_len:.1f} 字 (约 {avg_len/7:.1f} 秒)")

    st.download_button("导出无损分镜脚本", shot_content, file_name="director_script.txt")
