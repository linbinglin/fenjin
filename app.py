import streamlit as st
from openai import OpenAI
import re
import time
import math

# ====================
# 1. 页面配置与样式
# ====================
st.set_page_config(
    page_title="全能文案·电影感分镜系统 (V13 Stable)",
    page_icon="🎬",
    layout="wide"
)

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
    st.markdown("### ⚙️ 导演引擎 V13 设置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址 (Base URL)", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet", "gemini-pro", "grok-beta", "自定义"]
    selected_model = st.selectbox("Model ID (模型选择)", model_options)
    
    if selected_model == "自定义":
        model_id = st.text_input("请输入自定义模型名称", value="grok-4.1")
    else:
        model_id = selected_model
        
    st.info("ℹ️ V13更新：已启用强制切片模式，彻底解决长文截断问题。")

# ====================
# 3. 核心工具函数
# ====================

def clean_text_for_count(text):
    """纯净字数统计（去除所有标点符号和空格）"""
    if not text: return ""
    pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9]')
    return re.sub(pattern, '', text)

def safe_split_text(text, limit=600):
    """
    【强制分块算法 V2】
    优先按标点切分，如果单句过长或找不到标点，则强制按长度切分。
    确保不会因为一段话太长导致只有 1 个 chunk。
    """
    chunks = []
    current_chunk = ""
    
    # 1. 预处理：将常见的结束标点统一替换，方便切割
    # 保护性替换，防止 split 消耗掉标点
    text = text.replace("。", "。|").replace("！", "！|").replace("？", "？|").replace("\n", "|")
    
    # 2. 初步切割
    sentences = text.split("|")
    
    for sentence in sentences:
        if not sentence: continue
        
        # 如果当前块 + 新句子 超过限制，就封包
        if len(current_chunk) + len(sentence) > limit:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            # 极端情况：如果单句本身就超过 limit (比如500字没标点)，强制切断
            if len(sentence) > limit:
                # 强制切片
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
    """
    单个分块处理，增加重试机制
    """
    system_prompt = f"""
你是一个严格的文案分镜员。请对以下文本进行分镜处理。

【重要指令】：
1. **必须无损还原**：不得删减原文任何文字，不得总结，不得添加原文没有的描述。
2. **合并短句**：请尽量将同一场景下的动作和短对话合并，每行分镜控制在 **30-45个字符**。
3. **格式严格**：每行以数字开头，纯文本输出。
   例如：
   1.8岁那年家里穷得揭不开锅了
   2.怀孕的母亲带着我在寺外乞讨

【当前进度】：
这是全篇文案的第 {chunk_index + 1} / {total_chunks} 部分。请只处理这部分文本，不要自行结束故事。

待处理文本：
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
                temperature=0.3 # 低温保证准确性
            )
            content = response.choices[0].message.content
            if content:
                return content
        except Exception as e:
            if attempt == max_retries - 1:
                return f"Error: {e}"
            time.sleep(2)
    return "Error: Timeout"

# ====================
# 4. 主逻辑
# ====================

st.markdown('<div class="main-header">🎬 全能文案·电影感分镜系统 (V13 Stable)</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file and api_key:
    raw_content = uploaded_file.read().decode("utf-8")
    # 去除原文换行，强制变为一整段，交给算法重新切割
    clean_input = raw_content.replace("\n", "").replace("\r", "").strip()
    
    # 原文统计
    original_clean_len = len(clean_text_for_count(clean_input))
    
    st.info(f"📄 原文已加载，共 {len(clean_input)} 字符。正在准备分块处理...")

    if st.button("🚀 启动视觉无损分镜", type="primary"):
        
        # 1. 强制分块 (关键步骤)
        # 设定 limit=600，保证7000字至少会被切成 12-13 块
        chunks = safe_split_text(clean_input, limit=600)
        total_chunks = len(chunks)
        
        # 进度显示区
        progress_bar = st.progress(0)
        status_box = st.empty()
        result_area = st.empty()
        
        full_result_lines = []
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        start_time = time.time()
        
        # 2. 逐块处理
        for i, chunk in enumerate(chunks):
            status_box.markdown(f"""
            ### 🔄 正在处理第 {i+1} / {total_chunks} 剧情块
            - 当前块字数：{len(chunk)}
            - 已生成分镜：{len(full_result_lines)} 组
            """)
            
            chunk_result = process_chunk_with_retry(client, model_id, chunk, i, total_chunks)
            
            if "Error" in chunk_result:
                st.error(f"处理第 {i+1} 块时失败: {chunk_result}")
                break
            
            # 清洗每一块的结果 (去掉AI生成的序号，防止断层)
            lines = chunk_result.split('\n')
            for line in lines:
                # 正则：去掉行首的 "1." "1、" 等
                clean_line = re.sub(r'^\d+[.、]\s*', '', line).strip()
                if clean_line:
                    full_result_lines.append(clean_line)
            
            # 实时更新进度条
            progress_bar.progress((i + 1) / total_chunks)
            
        # 3. 最终汇总
        if full_result_lines:
            # 自动重新编号
            final_output = ""
            final_clean_text = ""
            for idx, line in enumerate(full_result_lines):
                final_output += f"{idx + 1}.{line}\n"
                final_clean_text += line
                
            final_clean_len = len(clean_text_for_count(final_clean_text))
            deviation = final_clean_len - original_clean_len
            
            # 保存到 session
            st.session_state['result'] = final_output
            st.session_state['orig_len'] = original_clean_len
            st.session_state['final_len'] = final_clean_len
            st.session_state['deviation'] = deviation
            st.session_state['shots'] = len(full_result_lines)
            st.session_state['chunks'] = total_chunks
            
            status_box.empty()
            st.rerun()

# ====================
# 5. 结果展示
# ====================

if 'result' in st.session_state:
    result = st.session_state['result']
    orig_len = st.session_state['orig_len']
    final_len = st.session_state['final_len']
    deviation = st.session_state['deviation']
    shots = st.session_state['shots']
    chunks = st.session_state['chunks']

    st.markdown("---")
    st.success(f"✅ 处理完成！已将 {orig_len} 字拆分为 {chunks} 个独立剧情块进行处理。")
    st.progress(1.0)

    # 数据面板
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-label">原文纯字数</div><div class="stat-value">{orig_len}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="stat-label">生成分镜总数</div><div class="stat-value">{shots} 组</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="stat-label">处理后纯字数</div><div class="stat-value">{final_len}</div></div>', unsafe_allow_html=True)
    with c4:
        # 偏差颜色逻辑
        if deviation == 0:
            color = "#28a745" # Green
            msg = "完美无损"
        elif abs(deviation) < 50:
            color = "#ffc107" # Yellow
            msg = "轻微偏差"
        else:
            color = "#dc3545" # Red
            msg = "严重偏差"
            
        st.markdown(f'<div class="stat-box"><div class="stat-label">偏差值 ({msg})</div><div class="stat-value" style="color:{color}">{deviation} 字</div></div>', unsafe_allow_html=True)

    if abs(deviation) > 100:
        st.error(f"⚠️ 依然存在字数偏差？建议：尝试更换模型（推荐使用 Claude-3.5 或 GPT-4o），部分小参数模型在长文本处理时容易丢字。")

    st.markdown("### 📝 视觉分镜编辑器 (无损还原)")
    st.text_area("生成结果", value=result, height=800)
    
    st.download_button("📥 下载分镜脚本", result, "storyboard_v13.txt")
