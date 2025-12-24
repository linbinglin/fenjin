import streamlit as st
from openai import OpenAI
import re
import time

# ====================
# 1. 页面配置与状态初始化
# ====================
st.set_page_config(
    page_title="全能文案·电影感分镜系统 (V16 视觉节奏版)",
    page_icon="🎬",
    layout="wide"
)

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
        border: 1px solid #ddd;
    }
    .stat-value {font-size: 2rem; font-weight: bold; color: #333;}
    textarea {
        font-family: 'Courier New', Courier, monospace; 
        font-size: 16px !important;
        line-height: 1.8 !important;
    }
    .stProgress > div > div > div > div {
        background-color: #007bff;
    }
</style>
""", unsafe_allow_html=True)

# ====================
# 2. 侧边栏
# ====================
with st.sidebar:
    st.markdown("### ⚙️ 导演引擎 V16")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet", "gemini-pro", "grok-beta", "自定义"]
    selected_model = st.selectbox("Model ID", model_options)
    
    if selected_model == "自定义":
        model_id = st.text_input("输入模型名称", value="grok-4.1")
    else:
        model_id = selected_model
        
    st.info("ℹ️ V16升级：已启用“贪婪聚合”策略。AI将尽可能合并短句，使单镜字数接近35字，大幅减少碎片化分镜。")

# ====================
# 3. 核心逻辑
# ====================

def clean_text_for_count(text):
    if not text: return ""
    pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9]')
    return re.sub(pattern, '', text)

def smart_sentence_split(text, max_chars=800):
    """
    分块给予AI足够的上下文（800字），让它有空间进行合并。
    """
    chunks = []
    current_chunk = ""
    parts = re.split(r'(。|！|？|\n)', text)
    temp_sentence = ""
    for part in parts:
        temp_sentence += part
        if part in ["。", "！", "？", "\n"]:
            if len(current_chunk) + len(temp_sentence) > max_chars:
                if current_chunk: chunks.append(current_chunk)
                current_chunk = temp_sentence
            else:
                current_chunk += temp_sentence
            temp_sentence = ""
    if temp_sentence: current_chunk += temp_sentence
    if current_chunk: chunks.append(current_chunk)
    return chunks

def process_chunk_merge_v16(client, model, text_chunk, index, total):
    """
    【V16 核心修正：贪婪聚合 Prompt】
    指令核心：除非字数爆了，否则死都不换行。
    """
    system_prompt = f"""
你是一个专业的【视频节奏剪辑师】。
你的目标是将原本琐碎的文案，合并成流畅的“画面脚本”。

【核心原则 - 必须严格遵守】：
1. **贪婪合并（关键）**：不要看到逗号就换行！请尽可能将连续的短句合并在同一行，**凑够 25-35 个字**。
   - 错误示例：
     1.皇上翻遍后宫
     2.只为找出那个宫女
   - 正确示例（合并）：
     1.皇上翻遍后宫，只为找出那个酒后爬龙床的宫女

2. **换行标准**：只有满足以下任一条件时，才允许换行：
   - 当前行字数已超过 **35个字**（这是硬性视觉上限）。
   - 发生了明显的**场景切换**（如从回忆回到现实）。
   - 发生了**角色对话**切换（A说完B说）。

3. **零偏差**：你可以合并行，但**绝对禁止**修改、删除或增加原文的任何一个汉字。

4. **输出格式**：纯文本，以数字序号开头。

这是文案的第 {index+1}/{total} 部分，请开始处理：
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_chunk}
            ],
            stream=False,
            temperature=0.2 # 稍微提高一点点温度，允许它进行合并操作的逻辑判断
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# ====================
# 4. 主程序
# ====================

st.markdown('<div class="main-header">🎬 全能文案·电影感分镜系统 (V16)</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file and api_key:
    raw_content = uploaded_file.read().decode("utf-8")
    # 预处理：去除原文的所有换行符，把文本变成一条长龙，方便AI重新剪辑
    clean_input_stream = raw_content.replace("\n", "").replace("\r", "")
    orig_len = len(clean_text_for_count(clean_input_stream))
    
    st.caption(f"📄 原文加载成功，共 {orig_len} 纯字。正在进行视觉节奏重组...")

    if st.button("🚀 启动视觉分镜 (合并模式)", type="primary"):
        
        # 使用较大的块(800字)以利于合并
        chunks = smart_sentence_split(clean_input_stream, max_chars=800)
        total_chunks = len(chunks)
        
        progress_bar = st.progress(0)
        status_box = st.empty()
        full_results = []
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        for i, chunk in enumerate(chunks):
            status_box.markdown(f"**⚡ 正在处理第 {i+1}/{total_chunks} 剧情块...** (正在执行短句聚合)")
            
            res = process_chunk_merge_v16(client, model_id, chunk, i, total_chunks)
            
            if "Error" in res:
                st.error(res)
                break
                
            lines = res.split('\n')
            for line in lines:
                # 提取内容
                cleaned = re.sub(r'^[\d\s\.\、]+', '', line).strip()
                if cleaned:
                    full_results.append(cleaned)
            
            progress_bar.progress((i + 1) / total_chunks)
            
        if full_results:
            final_text = ""
            combined_clean = ""
            for idx, txt in enumerate(full_results):
                final_text += f"{idx + 1}.{txt}\n"
                combined_clean += txt
            
            st.session_state['result'] = final_text
            st.session_state['orig_len'] = orig_len
            st.session_state['final_len'] = len(clean_text_for_count(combined_clean))
            st.session_state['deviation'] = st.session_state['final_len'] - orig_len
            st.session_state['shots'] = len(full_results)
            
            status_box.success("✅ 视觉分镜规划完成！短句已自动聚合。")
            time.sleep(0.5)
            st.rerun()

# ====================
# 5. 结果面板
# ====================

if st.session_state['result']:
    result = st.session_state['result']
    orig = st.session_state['orig_len']
    final = st.session_state['final_len']
    dev = st.session_state['deviation']
    shots = st.session_state['shots']
    
    st.markdown("---")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-label">原文纯字数</div><div class="stat-value">{orig}</div></div>', unsafe_allow_html=True)
    with c2:
        # 这里的数字应该会显著下降
        st.markdown(f'<div class="stat-box" style="border: 2px solid #007bff;"><div class="stat-label">生成分镜总数 (已合并)</div><div class="stat-value">{shots} 组</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="stat-label">处理后纯字数</div><div class="stat-value">{final}</div></div>', unsafe_allow_html=True)
    with c4:
        color = "#28a745" if dev == 0 else "#dc3545"
        st.markdown(f'<div class="stat-box"><div class="stat-label">偏差值</div><div class="stat-value" style="color:{color}">{dev} 字</div></div>', unsafe_allow_html=True)
        
    st.markdown("### 📝 视觉分镜编辑器")
    st.text_area("分镜结果", value=result, height=800)
    st.download_button("📥 下载 .txt", result, "storyboard_v16.txt")
