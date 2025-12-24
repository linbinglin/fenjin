import streamlit as st
from openai import OpenAI
import re
import time

# ====================
# 1. 页面配置与样式
# ====================
st.set_page_config(
    page_title="全能文案·电影感分镜系统 (V12 Pro)",
    page_icon="🎬",
    layout="wide"
)

# 注入CSS以复刻UI风格
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
    .stProgress > div > div > div > div {
        background-color: #007bff;
    }
    textarea {
        font-family: 'Courier New', Courier, monospace; /* 剧本常用等宽字体 */
    }
</style>
""", unsafe_allow_html=True)

# ====================
# 2. 侧边栏配置
# ====================
with st.sidebar:
    st.markdown("### ⚙️ 导演引擎 V12 设置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址 (Base URL)", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet", "gemini-pro", "grok-beta", "自定义"]
    selected_model = st.selectbox("Model ID (模型选择)", model_options)
    
    if selected_model == "自定义":
        model_id = st.text_input("请输入自定义模型名称", value="grok-4.1")
    else:
        model_id = selected_model

# ====================
# 3. 核心逻辑函数
# ====================

def clean_text_for_count(text):
    """纯净字数统计（去除所有标点符号和空格）"""
    if not text: return ""
    pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9]')
    return re.sub(pattern, '', text)

def split_text_into_chunks(text, max_chunk_size=1000):
    """
    智能分块算法：
    将长文本切分成多个块，防止AI处理长文时注意力丢失或“偷懒”。
    尽量在句号、感叹号处切分，保证语义完整。
    """
    chunks = []
    current_chunk = ""
    
    # 按句子粗略拆分
    sentences = re.split(r'(。|！|？|\n)', text)
    
    for part in sentences:
        if len(current_chunk) + len(part) < max_chunk_size:
            current_chunk += part
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = part
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def process_chunk(client, model, text_chunk, chunk_index, total_chunks):
    """
    单个剧情块的处理逻辑
    重点：Prompt要求“聚合”而非“拆散”
    """
    system_prompt = f"""
你是一个专业的电影分镜师。你的任务是将小说文本转换为紧凑的视频分镜脚本。
请严格按照以下**“聚合逻辑”**执行：

1. **核心目标**：将原本琐碎的短句，合并成一个完整的画面描述。不要每一句话都换行！
2. **时长控制**：每一行分镜的文案长度，必须控制在 **25-35个字符之间**（约5秒时长）。
   - 如果原文是 "他吃饭。他喝水。" -> 请合并为一行："1.他吃饭，又喝了一口水"
   - 只有当字数超过35字，或者场景/角色发生剧烈切换时，才允许换行。
3. **绝对无损**：必须包含原文所有信息，一个字都不能少，禁止删减，禁止添加原文没有的描述。
4. **格式**：纯文本输出，每行以数字开头，例如 "1. xxxxxx"。
5. **处理对象**：这是全书的第 {chunk_index + 1}/{total_chunks} 部分，请紧接上文逻辑。

待处理文本（忽略原有换行，重新规划）：
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text_chunk}
            ],
            stream=False,
            temperature=0.5 # 降低随机性，让聚合更稳定
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# ====================
# 4. 主界面逻辑
# ====================

st.markdown('<div class="main-header">🎬 全能文案·电影感分镜系统 (V12 Pro)</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file and api_key:
    raw_content = uploaded_file.read().decode("utf-8")
    # 预处理：移除原文换行，变成一整条数据流
    clean_input = raw_content.replace("\n", "").replace("\r", "").strip()
    original_len = len(clean_text_for_count(clean_input))
    
    st.info(f"📄 原文已加载，共 {len(clean_input)} 字符。")

    if st.button("🚀 启动视觉无损分镜", type="primary"):
        
        # 1. 切分剧情块
        chunks = split_text_into_chunks(clean_input, max_chunk_size=800) # 800字一块，保证AI注意力集中
        total_chunks = len(chunks)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        full_result = []
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        start_time = time.time()
        
        # 2. 循环处理每个块
        for i, chunk in enumerate(chunks):
            status_text.markdown(f"**正在处理剧情块 {i+1}/{total_chunks}**... (正在进行视觉单元规划)")
            
            chunk_result = process_chunk(client, model_id, chunk, i, total_chunks)
            
            if "Error" in chunk_result:
                st.error(f"处理第 {i+1} 块时出错: {chunk_result}")
                break
                
            # 清理AI返回的格式（去掉AI自己生成的序号，我们最后统一加）
            # 这一步很重要，防止AI生成的序号断层
            lines = chunk_result.split('\n')
            for line in lines:
                clean_line = re.sub(r'^\d+[\.、]\s*', '', line).strip()
                if clean_line:
                    full_result.append(clean_line)
            
            # 更新进度条
            progress_bar.progress((i + 1) / total_chunks)
        
        # 3. 最终组装
        status_text.success("✅ 分镜规划完成！正在进行全量稽核...")
        time.sleep(0.5)
        
        # 重新编号
        final_output = ""
        final_clean_text = ""
        for idx, line in enumerate(full_result):
            final_output += f"{idx + 1}.{line}\n"
            final_clean_text += line
            
        # 存入Session State
        st.session_state['final_output'] = final_output
        st.session_state['original_len'] = original_len
        st.session_state['final_clean_len'] = len(clean_text_for_count(final_clean_text))
        st.session_state['shot_count'] = len(full_result)
        st.session_state['chunks_count'] = total_chunks

# ====================
# 5. 结果面板 (UI复刻)
# ====================

if 'final_output' in st.session_state:
    out_text = st.session_state['final_output']
    orig_len = st.session_state['original_len']
    final_len = st.session_state['final_clean_len']
    shots = st.session_state['shot_count']
    deviation = final_len - orig_len
    chunks_num = st.session_state['chunks_count']

    st.markdown("---")
    
    # 进度条占位展示 (模拟图2)
    st.caption(f"📚 已识别 {chunks_num} 个独立剧情块，视觉单元规划完毕。")
    st.progress(100)

    # 数据统计卡片
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="stat-box"><div class="stat-label">原文纯字数</div><div class="stat-value">{orig_len}</div></div>', unsafe_allow_html=True)
    with c2:
        # 高亮显示分镜组数，这应该是现在的数值会少很多
        st.markdown(f'<div class="stat-box" style="border: 2px solid #28a745;"><div class="stat-label">生成分镜总数</div><div class="stat-value">{shots} 组</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="stat-box"><div class="stat-label">处理后纯字数</div><div class="stat-value">{final_len}</div></div>', unsafe_allow_html=True)
    with c4:
        color = "#d9534f" if deviation != 0 else "#28a745"
        st.markdown(f'<div class="stat-box"><div class="stat-label">偏差值 (标点除外)</div><div class="stat-value" style="color:{color}">{deviation} 字</div></div>', unsafe_allow_html=True)

    # 警告信息
    if deviation != 0:
        st.warning(f"⚠️ 警告：AI遗漏或添加了 {abs(deviation)} 个字，请检查文本末尾或过长段落。")
    else:
        st.success("✅ 完美！字数零偏差，内容无损还原。")

    # 编辑器
    st.markdown("### 📝 视觉分镜编辑器 (无损还原)")
    st.text_area("生成结果 (可直接复制)", value=out_text, height=600)
    
    st.download_button("📥 下载分镜文件", out_text, "storyboard.txt")
