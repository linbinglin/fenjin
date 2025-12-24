import streamlit as st
from openai import OpenAI
import re
import time

# ====================
# 1. 页面配置与防崩溃初始化
# ====================
st.set_page_config(
    page_title="全能文案·电影感分镜系统 (V15 终极修正版)",
    page_icon="🎬",
    layout="wide"
)

# 初始化Session State (防止刷新报错)
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
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stat-value {font-size: 2rem; font-weight: bold; color: #333;}
    .stat-label {font-size: 0.9rem; color: #666;}
    textarea {
        font-family: 'Courier New', Courier, monospace; 
        font-size: 16px !important;
        line-height: 1.8 !important;
    }
    .stProgress > div > div > div > div {
        background-color: #28a745;
    }
</style>
""", unsafe_allow_html=True)

# ====================
# 2. 侧边栏
# ====================
with st.sidebar:
    st.markdown("### ⚙️ 导演引擎 V15 (严谨版)")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet", "gemini-pro", "grok-beta", "自定义"]
    selected_model = st.selectbox("Model ID", model_options)
    
    if selected_model == "自定义":
        model_id = st.text_input("输入模型名称", value="grok-4.1")
    else:
        model_id = selected_model
        
    st.info("ℹ️ V15核心升级：\n1. 智能整句切分(防止断句丢字)\n2. 逐字复刻模式(禁止AI总结)")

# ====================
# 3. 核心逻辑：智能切分与处理
# ====================

def clean_text_for_count(text):
    """纯净字数统计（去标点）"""
    if not text: return ""
    pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9]')
    return re.sub(pattern, '', text)

def smart_sentence_split(text, max_chars=600):
    """
    【V15 智能整句切分算法】
    绝对不切断句子。寻找句号、感叹号、问号进行安全分割。
    保证每一块发给AI的都是完整的语义块。
    """
    chunks = []
    current_chunk = ""
    
    # 1. 先用正则按句子结束符切分 (保留分隔符)
    # 匹配 。！？ 以及换行符，放到列表中
    parts = re.split(r'(。|！|？|\n)', text)
    
    temp_sentence = ""
    
    # 2. 重新组装
    for part in parts:
        temp_sentence += part
        # 如果 part 是标点，说明一个句子结束了
        if part in ["。", "！", "？", "\n"]:
            # 检查加入当前块是否会超标
            if len(current_chunk) + len(temp_sentence) > max_chars:
                # 超标了，先保存当前块
                if current_chunk:
                    chunks.append(current_chunk)
                # 新起一块
                current_chunk = temp_sentence
            else:
                # 没超标，接上去
                current_chunk += temp_sentence
            temp_sentence = ""
            
    # 处理剩余部分
    if temp_sentence:
        current_chunk += temp_sentence
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def process_chunk_strict(client, model, text_chunk, index, total):
    """
    【V15 逐字复刻 Prompt】
    核心改变：不再要求AI“理解剧情”，而是要求它做“排版工”。
    这能最大程度防止AI改写或遗漏内容。
    """
    system_prompt = f"""
你是一个严格的【字幕排版引擎】。你的任务不是写作，而是对现有文本进行换行排版。

【严格执行以下 3 条死命令】：
1. **逐字复刻**：输出的内容必须与输入完全一致，**禁止修改、删除、增加任何一个汉字**。禁止进行摘要或总结！
2. **排版逻辑**：
   - 将长段落拆解为短句，每行 **25-35个字符**。
   - 遇到对话、动作切换时换行。
   - 如果一句话太短（少于10字）且与下一句关联紧密，请合并到同一行，但不要超过35字。
3. **输出格式**：纯文本，每行开头标数字序号。

输入文本片段 ({index+1}/{total})：
{text_chunk}

请输出排版后的结果：
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_chunk}
            ],
            stream=False,
            temperature=0.1 # 极低温度，扼杀AI的创造欲，只保留执行力
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# ====================
# 4. 主程序
# ====================

st.markdown('<div class="main-header">🎬 全能文案·电影感分镜系统 (V15)</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file and api_key:
    raw_content = uploaded_file.read().decode("utf-8")
    # 去除多余空格和空行，整理成紧凑流
    clean_input = re.sub(r'\s+', '', raw_content).replace("\n", "")
    # 恢复标点后的自然停顿（可选，防止太密）
    # 但为了绝对匹配，我们直接处理 clean_input
    
    orig_len = len(clean_text_for_count(clean_input))
    st.caption(f"📄 原文已加载，共 {orig_len} 纯净字符。")

    if st.button("🚀 启动高保真分镜", type="primary"):
        
        # 1. 智能切分
        chunks = smart_sentence_split(raw_content, max_chars=500) # 500字更安全
        total_chunks = len(chunks)
        
        # 验证切分是否丢字
        test_len = sum([len(c) for c in chunks])
        # st.write(f"切分完整性检查: 原文{len(raw_content)} vs 切块总和{test_len}") 
        
        progress_bar = st.progress(0)
        status_box = st.empty()
        full_results = []
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        start_time = time.time()
        
        # 2. 逐块处理
        for i, chunk in enumerate(chunks):
            status_box.markdown(f"**⚡ 正在排版第 {i+1}/{total_chunks} 区块...** (严谨模式)")
            
            res = process_chunk_strict(client, model_id, chunk, i, total_chunks)
            
            if "Error" in res:
                st.error(f"处理中断: {res}")
                break
                
            # 清洗AI输出的序号
            lines = res.split('\n')
            for line in lines:
                # 提取内容，去除首尾空白
                # 兼容格式: "1. 内容" 或 "1、内容" 或 "1 内容"
                cleaned = re.sub(r'^[\d\s\.\、]+', '', line).strip()
                if cleaned:
                    full_results.append(cleaned)
            
            progress_bar.progress((i + 1) / total_chunks)
            
        # 3. 结果组装
        if full_results:
            final_text = ""
            combined_clean_text = ""
            for idx, txt in enumerate(full_results):
                final_text += f"{idx + 1}.{txt}\n"
                combined_clean_text += txt
            
            # 存入状态
            st.session_state['result'] = final_text
            st.session_state['orig_len'] = orig_len
            st.session_state['final_len'] = len(clean_text_for_count(combined_clean_text))
            st.session_state['deviation'] = st.session_state['final_len'] - orig_len
            st.session_state['shots'] = len(full_results)
            st.session_state['chunks'] = total_chunks
            
            status_box.success("✅ 全量排版完成！")
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
    
    # 统计卡片
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-label">原文纯字数</div><div class="stat-value">{orig}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="stat-box"><div class="stat-label">生成分镜总数</div><div class="stat-value">{shots} 组</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="stat-label">处理后纯字数</div><div class="stat-value">{final}</div></div>', unsafe_allow_html=True)
    with c4:
        # 偏差逻辑：允许极小误差（可能是AI把英文标点转中文标点导致的正则误差）
        if abs(dev) < 10:
            color = "#28a745"
            msg = "完美"
        elif abs(dev) < 50:
            color = "#ffc107"
            msg = "轻微偏差"
        else:
            color = "#dc3545"
            msg = "严重偏差"
        st.markdown(f'<div class="stat-box"><div class="stat-label">偏差值 ({msg})</div><div class="stat-value" style="color:{color}">{dev} 字</div></div>', unsafe_allow_html=True)
        
    if dev < -50:
        st.error(f"⚠️ 依然存在丢字现象 (-{abs(dev)})？这通常是因为模型不够智能。建议使用 GPT-4o 或 Claude-3.5，它们对“逐字复刻”指令的执行力远强于 grok/deepseek-chat。")

    st.markdown("### 📝 视觉分镜编辑器")
    st.text_area("分镜结果", value=result, height=800)
    st.download_button("📥 下载 .txt", result, "final_storyboard.txt")
