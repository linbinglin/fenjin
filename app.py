import streamlit as st
from openai import OpenAI
import re
import pandas as pd
import time

# --- 页面配置 ---
st.set_page_config(
    page_title="分镜引擎 V4.0 (智能缝合版)",
    page_icon="🎬",
    layout="wide"
)

# --- CSS样式 ---
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; color: #333; font-weight: 700; }
    .stDataFrame { border: 1px solid #ddd; }
    div[data-testid="stMetricValue"] { font-size: 1.2rem; }
</style>
""", unsafe_allow_html=True)

# --- 核心工具函数 ---

def count_valid_chars(text):
    """统计有效字数"""
    if not text: return 0
    clean_text = re.sub(r'[^\w\u4e00-\u9fa50-9]', '', text)
    return len(clean_text)

def analyze_rhythm(text):
    """分析分镜节奏状态"""
    length = count_valid_chars(text)
    if length == 0: return "❌ 空白", length
    if length < 10: return "🟡 较短 (快节奏)", length
    if 10 <= length <= 38: return "✅ 完美 (5秒)", length
    return "🔴 较长 (需关注)", length

def smart_chunking(text, max_chunk_size=1000):
    """分块防止幻觉"""
    sentences = re.split(r'(?<=[。！？!?])', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chunk_size:
            current_chunk += sentence
        else:
            if current_chunk: chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk: chunks.append(current_chunk)
    return chunks

def post_process_merge(lines, max_chars=35, min_chars=12):
    """
    【V4.0 核心算法：视觉胶水】
    强制遍历 AI 输出的列表。
    如果发现某行太短（< min_chars），且加上下一行不超过 max_chars，
    则强制合并，治愈“碎片症”。
    """
    if not lines: return []
    
    merged_lines = []
    buffer = lines[0] # 初始化缓冲区
    
    for i in range(1, len(lines)):
        current_line = lines[i]
        buffer_len = count_valid_chars(buffer)
        current_len = count_valid_chars(current_line)
        
        # 核心判断逻辑：
        # 1. 如果缓冲区太短 (比如 "毫无用处" 4个字)
        # 2. 并且合并后总长度不仅没有超标
        # 3. 或者缓冲区本身没有结尾标点（说明话没说完）
        should_merge = False
        
        # 规则 A: 极短碎片强制合并
        if buffer_len < min_chars and (buffer_len + current_len <= max_chars):
            should_merge = True
        
        # 规则 B: 话没说完（无标点）尝试合并
        if not re.search(r'[。！？!?]$', buffer) and (buffer_len + current_len <= max_chars):
             should_merge = True

        if should_merge:
            buffer += current_line # 缝合
        else:
            merged_lines.append(buffer) # 释放缓冲区
            buffer = current_line # 新的缓冲区
            
    merged_lines.append(buffer) # 最后的残留
    return merged_lines

# --- 侧边栏 ---
with st.sidebar:
    st.markdown("## ⚙️ 引擎设置 V4.0")
    base_url = st.text_input("Base URL", value="https://blog.tuiwen.xyz/v1")
    api_key = st.text_input("API Key", type="password")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.divider()
    st.markdown("### 🔧 碎片修复强度")
    min_merge_len = st.slider("最小分镜字数 (低于此值将尝试合并)", 5, 20, 12, 
                              help="如果分镜小于这个字数，算法会强制将其与下一行合并（除非合并后太长）。调大此值可减少碎片。")

# --- 主界面 ---
st.markdown('<div class="main-header">🎬 分镜引擎 V4.0 (智能缝合版)</div>', unsafe_allow_html=True)
st.markdown("##### 🚀 核心特性：分块抗幻觉 + Python视觉胶水(修复碎片)")
st.divider()

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=["txt"])

if uploaded_file is not None:
    raw_text = uploaded_file.read().decode("utf-8")
    flattened_text = raw_text.replace('\n', '').replace('\r', '').strip()
    input_count = count_valid_chars(flattened_text)

    st.success(f"原文装载完毕 | {input_count} 字")
    
    if st.button("⚡ 启动生成", type="primary"):
        if not api_key:
            st.error("缺少 API Key"); st.stop()

        # 1. 智能分块
        chunks = smart_chunking(flattened_text)
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        raw_ai_lines = []
        progress_bar = st.progress(0)
        status = st.empty()
        
        # 2. AI 粗剪
        for i, chunk in enumerate(chunks):
            status.text(f"正在分析第 {i+1}/{len(chunks)} 区块...")
            
            # Prompt 侧重于语义完整性，不再过分强调短句，因为后面有Python代码把关
            system_prompt = f"""
你是一个专业分镜师。请对以下文本进行分镜处理。

【重要原则】
1. **优先保持语义完整**：不要为了换行而切断“主语-谓语-宾语”结构。
   - 错误：最终柳丞相 / 和贵妃 / 被判处腰斩
   - 正确：最终柳丞相和贵妃被判处腰斩
2. **禁止幻觉**：绝对不要增加原文没有的字，不要删减。
3. **换行逻辑**：仅在“动作切换”、“场景切换”或“句子确实太长(>35字)”时换行。

【文本】
{chunk}

请输出纯文本，每行一句，不要带序号。
"""
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "你是一个严谨的分镜师。保持句意完整是第一优先级。"},
                        {"role": "user", "content": system_prompt}
                    ],
                    temperature=0.1,
                )
                chunk_res = response.choices[0].message.content
                # 收集所有行，去除空行
                lines = [line.strip() for line in chunk_res.split('\n') if line.strip()]
                # 去除可能存在的序号
                lines = [re.sub(r'^\d+[\.、]\s*', '', line) for line in lines]
                raw_ai_lines.extend(lines)
                progress_bar.progress((i + 1) / len(chunks))
                
            except Exception as e:
                st.error(f"处理出错: {e}"); break
        
        status.text("🤖 AI 处理完毕，正在进行“视觉胶水”缝合运算...")
        
        # 3. Python 强力缝合 (核心修正步骤)
        # 调用我们写的算法，把碎片粘起来
        final_lines = post_process_merge(raw_ai_lines, max_chars=38, min_chars=min_merge_len)
        
        # 4. 构建输出
        final_text = ""
        valid_chars = 0
        data_list = []
        
        for idx, line in enumerate(final_lines):
            line_len = count_valid_chars(line)
            valid_chars += line_len
            rhythm, _ = analyze_rhythm(line)
            
            final_text += f"{idx+1}.{line}\n"
            data_list.append({
                "序号": idx+1,
                "分镜内容": line,
                "字数": line_len,
                "状态": rhythm
            })

        # 5. 展示
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📝 最终分镜")
            st.text_area("结果", value=final_text, height=600)
            
        with col2:
            st.subheader("📊 效果稽核")
            diff = valid_chars - input_count
            st.metric("字数偏差", f"{diff} 字", delta_color="off" if diff==0 else "inverse")
            if abs(diff) > 20:
                st.warning("字数偏差较大，请检查")
            else:
                st.success("字数匹配完美")
                
            df = pd.DataFrame(data_list)
            
            def highlight(val):
                if '❌' in val: return 'background-color: #ffcccc'
                if '🟡' in val: return 'background-color: #fff8dc' # 只有极短时才黄
                return ''

            st.dataframe(
                df.style.map(highlight, subset=['状态']),
                use_container_width=True,
                height=500,
                column_config={
                    "序号": st.column_config.NumberColumn(width="small"),
                    "分镜内容": st.column_config.TextColumn(width="large"),
                    "字数": st.column_config.ProgressColumn(format="%d", max_value=40)
                }
            )
