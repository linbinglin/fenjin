import streamlit as st
from openai import OpenAI
import re
import time

# ====================
# 1. 页面配置与状态初始化 (修复KeyError的核心)
# ====================
st.set_page_config(
    page_title="全能文案·电影感分镜系统 (V14 防崩溃版)",
    page_icon="🎬",
    layout="wide"
)

# --- 核心修复：初始化所有Session State变量 ---
# 这一步保证了无论怎么刷新，变量都存在，绝不会报 KeyError
if 'init' not in st.session_state:
    st.session_state['init'] = True
    st.session_state['result'] = ""
    st.session_state['orig_len'] = 0
    st.session_state['final_len'] = 0
    st.session_state['deviation'] = 0
    st.session_state['shots'] = 0
    st.session_state['chunks'] = 0

st.markdown("""
<style>
    .main-header {font-size: 2rem; font-weight: bold; margin-bottom: 1rem;}
    .stat-box {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e0e0e0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stat-value {font-size: 2.2rem; font-weight: bold; color: #333;}
    .stat-label {font-size: 0.9rem; color: #666; margin-top: 5px;}
    textarea {
        font-family: 'Courier New', Courier, monospace; 
        font-size: 16px !important;
    }
    .stProgress > div > div > div > div {
        background-color: #00CC66;
    }
</style>
""", unsafe_allow_html=True)

# ====================
# 2. 侧边栏配置
# ====================
with st.sidebar:
    st.markdown("### ⚙️ 导演引擎 V14 设置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址 (Base URL)", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet", "gemini-pro", "grok-beta", "自定义"]
    selected_model = st.selectbox("Model ID (模型选择)", model_options)
    
    if selected_model == "自定义":
        model_id = st.text_input("请输入自定义模型名称", value="grok-4.1")
    else:
        model_id = selected_model

# ====================
# 3. 工具函数
# ====================

def clean_text_for_count(text):
    """纯净字数统计"""
    if not text: return ""
    pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9]')
    return re.sub(pattern, '', text)

def safe_split_text(text, limit=600):
    """强制分块算法 (保留V13的优秀逻辑)"""
    chunks = []
    current_chunk = ""
    # 保护性替换
    text = text.replace("。", "。|").replace("！", "！|").replace("？", "？|").replace("\n", "|")
    sentences = text.split("|")
    
    for sentence in sentences:
        if not sentence: continue
        if len(current_chunk) + len(sentence) > limit:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            if len(sentence) > limit:
                for i in range(0, len(sentence), limit):
                    chunks.append(sentence[i:i+limit])
            else:
                current_chunk = sentence
        else:
            current_chunk += sentence
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def process_chunk_with_retry(client, model, text_chunk, chunk_index, total_chunks):
    """单个分块处理"""
    system_prompt = f"""
你是一个严格的文案分镜员。
1. **无损还原**：不得删减原文，不得添加原文没有的描述。
2. **合并短句**：将动作连贯的短句合并，每行分镜控制在 **30-45个字符**。
3. **格式**：每行以数字开头。
这是全篇文案的第 {chunk_index + 1} / {total_chunks} 部分。
"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text_chunk}
                ],
                stream=False,
                temperature=0.3
            )
            content = response.choices[0].message.content
            if content: return content
        except Exception as e:
            if attempt == max_retries - 1: return f"Error: {e}"
            time.sleep(1)
    return "Error: Timeout"

# ====================
# 4. 主逻辑
# ====================

st.markdown('<div class="main-header">🎬 全能文案·电影感分镜系统 (V14 Stable)</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file and api_key:
    raw_content = uploaded_file.read().decode("utf-8")
    clean_input = raw_content.replace("\n", "").replace("\r", "").strip()
    
    # 临时显示原文统计
    current_orig_len = len(clean_text_for_count(clean_input))
    st.caption(f"📄 原文已加载，共 {current_orig_len} 纯净字符。")

    if st.button("🚀 启动视觉无损分镜", type="primary"):
        chunks = safe_split_text(clean_input, limit=600)
        total_chunks = len(chunks)
        
        progress_bar = st.progress(0)
        status_box = st.empty()
        full_result_lines = []
        
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            for i, chunk in enumerate(chunks):
                status_box.info(f"🔄 正在处理第 {i+1}/{total_chunks} 剧情块...")
                chunk_result = process_chunk_with_retry(client, model_id, chunk, i, total_chunks)
                
                if "Error" in chunk_result:
                    st.error(f"处理第 {i+1} 块失败: {chunk_result}")
                    break
                
                lines = chunk_result.split('\n')
                for line in lines:
                    clean_line = re.sub(r'^\d+[.、]\s*', '', line).strip()
                    if clean_line:
                        full_result_lines.append(clean_line)
                
                progress_bar.progress((i + 1) / total_chunks)
            
            # 汇总结果并写入 Session State
            if full_result_lines:
                final_output = ""
                final_clean_text = ""
                for idx, line in enumerate(full_result_lines):
                    final_output += f"{idx + 1}.{line}\n"
                    final_clean_text += line
                
                # 更新状态
                st.session_state['result'] = final_output
                st.session_state['orig_len'] = current_orig_len
                st.session_state['final_len'] = len(clean_text_for_count(final_clean_text))
                st.session_state['deviation'] = st.session_state['final_len'] - st.session_state['orig_len']
                st.session_state['shots'] = len(full_result_lines)
                st.session_state['chunks'] = total_chunks
                
                status_box.success("✅ 处理完成！")
                time.sleep(0.5)
                st.rerun() # 刷新页面以显示结果
                
        except Exception as e:
            st.error(f"发生系统错误: {e}")

# ====================
# 5. 结果展示 (从 Session State 安全读取)
# ====================

# 只有当 result 不为空时才显示结果面板
if st.session_state['result']:
    result = st.session_state['result']
    orig_len = st.session_state['orig_len']
    final_len = st.session_state['final_len']
    deviation = st.session_state['deviation']
    shots = st.session_state['shots']
    chunks = st.session_state['chunks']

    st.markdown("---")
    st.caption(f"✅ 系统将原文拆解为 {chunks} 个独立剧情块进行高精度处理。")
    st.progress(1.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-label">原文纯字数</div><div class="stat-value">{orig_len}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="stat-label">生成分镜总数</div><div class="stat-value">{shots} 组</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="stat-label">处理后纯字数</div><div class="stat-value">{final_len}</div></div>', unsafe_allow_html=True)
    with c4:
        if deviation == 0:
            color, msg = "#28a745", "完美无损"
        elif abs(deviation) < 50:
            color, msg = "#ffc107", "轻微偏差"
        else:
            color, msg = "#dc3545", "严重偏差"
        st.markdown(f'<div class="stat-box"><div class="stat-label">偏差值 ({msg})</div><div class="stat-value" style="color:{color}">{deviation} 字</div></div>', unsafe_allow_html=True)

    st.markdown("### 📝 视觉分镜编辑器")
    st.text_area("生成结果", value=result, height=800)
    st.download_button("📥 下载分镜脚本", result, "storyboard_v14.txt")
