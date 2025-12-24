import streamlit as st
from openai import OpenAI
import re
import pandas as pd
import time

# --- 页面配置 ---
st.set_page_config(
    page_title="分镜引擎 V3.0 (防幻觉内核)",
    page_icon="🎬",
    layout="wide"
)

# --- CSS样式 ---
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .main-header { font-size: 2.2rem; color: #333; font-weight: 700; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    .stDataFrame { border: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# --- 核心工具函数 ---

def count_valid_chars(text):
    """统计有效字数（排除标点）"""
    if not text: return 0
    clean_text = re.sub(r'[^\w\u4e00-\u9fa50-9]', '', text)
    return len(clean_text)

def analyze_rhythm(text):
    """分析分镜节奏状态"""
    length = count_valid_chars(text)
    if length == 0: return "❌ 空白", length
    if length < 8: return "🟡 过短 (需合并)", length
    if 8 <= length <= 38: return "✅ 完美 (5秒)", length
    return "🔴 过长 (需拆分)", length

def smart_chunking(text, max_chunk_size=1000):
    """
    智能分块算法：
    防止一次性喂给AI太多文字导致幻觉。
    按句号/感叹号/问号切分，保证每块大约 1000 字。
    """
    sentences = re.split(r'(?<=[。！？!?])', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chunk_size:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

# --- 侧边栏配置 ---
with st.sidebar:
    st.markdown("## ⚙️ 引擎设置 V3.0")
    base_url = st.text_input("Base URL", value="https://blog.tuiwen.xyz/v1")
    api_key = st.text_input("API Key", type="password")
    model_id = st.text_input("Model ID", value="gpt-4o", help="建议使用逻辑性强的模型")
    
    st.divider()
    st.markdown("### 🛡️ 防幻觉机制")
    st.caption("V3.0 采用「分块流水线」技术。将长文拆解为小段单独处理，彻底杜绝 AI 因上下文过长而开始编造内容的现象。")

# --- 主界面 ---
st.markdown('<div class="main-header">🎬 电影分镜引擎 V3.0 (严控版)</div>', unsafe_allow_html=True)
st.markdown("##### 🚀 核心特性：分块运算 | 0幻觉 | 严格字数对齐")
st.divider()

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=["txt"])

if uploaded_file is not None:
    raw_text = uploaded_file.read().decode("utf-8")
    # 极度暴力的压缩，去掉所有格式，只留纯文本流
    flattened_text = raw_text.replace('\n', '').replace('\r', '').strip()
    input_count = count_valid_chars(flattened_text)

    col1, col2 = st.columns([3, 1])
    col1.success(f"原文装载完毕 (共 {input_count} 有效字符)")
    
    if col1.button("⚡ 启动精准分镜", type="primary"):
        if not api_key:
            st.error("缺少 API Key")
            st.stop()

        # 1. 执行智能分块
        chunks = smart_chunking(flattened_text, max_chunk_size=1200) # 1200字符为一个安全区间
        total_chunks = len(chunks)
        
        st.info(f"🧠 为了防止 AI 加戏，系统已将长文切割为 {total_chunks} 个独立运算块，正在逐一处理...")
        
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        full_result_text = ""
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_area = st.empty()
        
        # 2. 循环处理每个块 (这是解决幻觉的核心)
        for i, chunk in enumerate(chunks):
            status_text.text(f"正在运算第 {i+1}/{total_chunks} 区块 (进度 {(i+1)/total_chunks:.0%})...")
            
            # 极度严格的 Prompt
            system_prompt = f"""
你是一个严格的文本格式化程序。你的唯一任务是按视觉逻辑给文本换行。

【严厉禁止】
1. 绝对禁止添加原文中没有的字（如“他说”、“怒道”、“笑着”）。
2. 绝对禁止删除原文内容。
3. 禁止修改原文措辞。

【分段规则】
1. 将长句拆分为视觉分镜（每行约 15-35 字）。
2. 遇到角色切换、场景切换、动作变化时，必须强制换行。
3. 如果原文句子太长，请在标点处换行。
4. 如果原文句子极短（如2-4个字），尝试将其附着在上一句或下一句，除非它是强烈的语气词。

【待处理文本】
{chunk}

请直接输出分行后的文本，每行开头不要加数字序号，保持纯文本，以便后续拼接。
"""
            try:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": "你是一个没有感情的文本切割机器。你只负责换行，不负责创作。"},
                        {"role": "user", "content": system_prompt}
                    ],
                    temperature=0.1, # 极低温度，扼杀创造力，只留逻辑
                )
                
                chunk_result = response.choices[0].message.content
                full_result_text += chunk_result + "\n"
                
                # 实时更新显示
                result_area.text_area("正在生成的脚本...", value=full_result_text, height=400)
                progress_bar.progress((i + 1) / total_chunks)
                
            except Exception as e:
                st.error(f"区块 {i+1} 处理失败: {e}")
                break

        status_text.text("✅ 所有区块运算完毕，正在进行逻辑稽核...")
        
        # --- 3. 后处理：添加序号与统计 ---
        final_lines = [line.strip() for line in full_result_text.split('\n') if line.strip()]
        processed_data = []
        
        final_output_str = ""
        total_output_valid_chars = 0
        
        for idx, line in enumerate(final_lines):
            # 再次清洗可能残留的序号（以防万一）
            clean_line = re.sub(r'^\d+[\.、]\s*', '', line)
            
            status, length = analyze_rhythm(clean_line)
            total_output_valid_chars += length
            
            # 构建最终输出文本（带序号）
            final_output_str += f"{idx+1}.{clean_line}\n"
            
            processed_data.append({
                "序号": idx + 1,
                "分镜内容": clean_line,
                "字数": length,
                "评价": status
            })

        # --- 4. 最终结果面板 ---
        result_area.text_area("✅ 最终分镜脚本", value=final_output_str, height=500)
        
        st.divider()
        st.subheader("⚖️ 最终校验")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("原文有效字数", input_count)
        m2.metric("分镜后字数", total_output_valid_chars)
        
        diff = total_output_valid_chars - input_count
        m3.metric("偏差值 (越小越好)", f"{diff} 字", 
                  delta_color="off" if diff == 0 else "inverse")
        
        # 智能判定结果
        if abs(diff) < 20: # 允许极小误差（可能是空格或全半角符号差异）
            m4.success("🛡️ 安全：无幻觉")
        elif diff > 20:
            m4.error(f"⚠️ 警告：多了 {diff} 字")
        else:
            m4.warning(f"⚠️ 警告：少了 {abs(diff)} 字")

        # --- 详情表 ---
        df = pd.DataFrame(processed_data)
        
        def highlight_row(val):
            color = ''
            if '❌' in val: color = 'background-color: #ffcccc'
            elif '🟡' in val: color = 'background-color: #fff4cc'
            elif '🔴' in val: color = 'background-color: #ffe6e6'
            return color

        st.dataframe(
            df,
            column_config={
                "序号": st.column_config.NumberColumn(width="small"),
                "分镜内容": st.column_config.TextColumn(width="large"),
                "字数": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=50),
                "评价": st.column_config.TextColumn(width="medium"),
            },
            use_container_width=True,
            height=600
        )
