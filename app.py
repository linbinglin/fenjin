import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# ==========================================
# 🛠️ 核心工具函数库
# ==========================================

def smart_chunk_text(text, max_chars=1200):
    chunks = []
    while len(text) > max_chars:
        split_index = -1
        for mark in ["\n\n", "。", "！", "？"]:
            pos = text.rfind(mark, 0, max_chars)
            split_index = max(split_index, pos)
        if split_index == -1: split_index = max_chars
        else: split_index += 1 
        chunks.append(text[:split_index].strip())
        text = text[split_index:]
    if text.strip(): chunks.append(text.strip())
    return chunks

def get_pure_text(text):
    """只保留汉字数字，用于精确核对偏差"""
    text = re.sub(r'^\d+[\.、]\s*', '', text, flags=re.MULTILINE)
    return re.sub(r'[^\u4e00-\u9fa50-9]', '', text)

def renumber_content(text):
    """重排序号"""
    lines = text.split('\n')
    new_lines = []
    counter = 1
    for line in lines:
        stripped = line.strip()
        if not stripped: continue
        clean = re.sub(r'^\d+[\.、]\s*', '', stripped)
        new_lines.append(f"{counter}. {clean}")
        counter += 1
    return "\n".join(new_lines)

def recursive_split(text, threshold=38):
    """
    递归切分工具（保留给用户手动修剪长句用）
    """
    text = text.strip()
    if not text: return []
    if len(text) <= threshold: return [text]
    
    mid = len(text) // 2
    split_idx = -1
    for i in range(mid, 5, -1):
        if text[i] in ['，', ',', ' ', '；', ';', '。', '！', '？', '：', ':']:
            split_idx = i + 1
            break
            
    if split_idx == -1: split_idx = threshold 
        
    part1 = text[:split_idx].strip()
    part2 = text[split_idx:].strip()
    return recursive_split(part1, threshold) + recursive_split(part2, threshold)

def auto_split_all_lines(full_text, threshold=38):
    lines = full_text.split('\n')
    final_lines = []
    for line in lines:
        clean_line = re.sub(r'^\d+[\.、]\s*', '', line.strip())
        final_lines.extend(recursive_split(clean_line, threshold))
    return renumber_content("\n".join(final_lines))

# ==========================================
# 🎨 页面配置与状态管理
# ==========================================
st.set_page_config(page_title="导演引擎 V19-叙事聚合版", layout="wide", page_icon="🎬")

if 'generated_storyboard' not in st.session_state:
    st.session_state.generated_storyboard = ""
if 'original_text_pure_len' not in st.session_state:
    st.session_state.original_text_pure_len = 0
if 'editor_key' not in st.session_state:
    st.session_state.editor_key = 0

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V19")
    st.caption("Visual Aggregation Logic")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") 
    
    st.divider()
    st.info("💡 V19 核心调整：针对‘太碎’问题，增强了连贯叙事的合并能力。")

# ==========================================
# 🖥️ 主界面
# ==========================================
st.title("🎬 全能文案·电影感分镜系统 (V19)")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    pure_raw = get_pure_text(raw_text)
    
    if st.session_state.original_text_pure_len == 0 or len(pure_raw) != st.session_state.original_text_pure_len:
         st.session_state.original_text_pure_len = len(pure_raw)

    st.subheader("📊 视觉逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文汉字数", f"{st.session_state.original_text_pure_len} 字")

    if st.button("🚀 启动 V19 智能分镜", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                chunks = smart_chunk_text(raw_text)
                
                status = st.empty()
                status.info("正在执行 V19 视觉聚合指令...")
                
                full_result_list = []
                current_shot_idx = 1
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    # ==========================================
                    # 🔥 V19 Prompt: 强调“语义完整”和“合并短句”
                    # ==========================================
                    system_prompt = f"""你是一个懂得“镜头语言”的导演。请将文案转化为分镜列表。

【核心心法：聚合与切分】
你的目标是生成**饱满**的镜头（每行约 20-35 字），而不是碎片。

1. **叙事合并（重要！）**：
   - 遇到连续的短句描述、内心独白、连贯动作，只要总字数不超过 35 字，**必须合并**在同一行！
   - ❌ 错误（太碎）：
     1. 让我坐在旁边
     2. 亲手画下他们缠绵的每一幕
   - ✅ 正确（画面完整）：
     1. 让我坐在旁边，亲手画下他们缠绵的每一幕

2. **对话切分**：
   - 只有当【说话人改变】或【对话与心理活动混杂】时，才必须换行。
   
3. **节奏控制**：
   - 理想长度：20-35 字。
   - 除非句子极短（<5字）且表示强调，否则不要单独成行。

4. **无损还原**：保留所有汉字。

【起始编号】：{current_shot_idx}
"""
                    clean_chunk = re.sub(r'\s+', '', chunk)
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "system", "content": system_prompt},
                                  {"role": "user", "content": clean_chunk}],
                        temperature=0.2 # 稍微提高一点点温度，让它敢于合并
                    )
                    chunk_res = response.choices[0].message.content.strip()
                    full_result_list.append(chunk_res)
                    
                    last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                    if last_nums: current_shot_idx = int(last_nums[-1]) + 1
                    progress_bar.progress((idx + 1) / len(chunks))
                
                raw_combined = "\n".join(full_result_list)
                st.session_state.generated_storyboard = renumber_content(raw_combined)
                st.session_state.editor_key += 1 
                st.rerun()

            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.divider()

    # ==========================================
    # 📝 核心交互区
    # ==========================================
    if st.session_state.generated_storyboard:
        col_edit, col_analyze = st.columns([1.8, 1.2])
        
        with col_edit:
            st.subheader("🎬 分镜编辑器")
            
            b1, b2 = st.columns([1, 1])
            with b1:
                if st.button("🔄 仅重置序号", use_container_width=True):
                    formatted = renumber_content(st.session_state.generated_storyboard)
                    st.session_state.generated_storyboard = formatted
                    st.session_state.editor_key += 1 
                    st.rerun()
            
            with b2:
                # 保留剪刀工具，以防万一
                if st.button("✂️ 强力切分 (>38字)", type="secondary", use_container_width=True):
                    split_text = auto_split_all_lines(st.session_state.generated_storyboard, threshold=38)
                    st.session_state.generated_storyboard = split_text
                    st.session_state.editor_key += 1 
                    st.rerun()

            current_val = st.text_area(
                "editor",
                value=st.session_state.generated_storyboard,
                height=600,
                key=f"editor_area_{st.session_state.editor_key}", 
                label_visibility="collapsed"
            )
            
            if current_val != st.session_state.generated_storyboard:
                st.session_state.generated_storyboard = current_val

        with col_analyze:
            st.subheader("📈 数据校验")
            current_text = st.session_state.generated_storyboard
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            
            output_pure = get_pure_text(current_text)
            diff = len(output_pure) - st.session_state.original_text_pure_len
            
            c1, c2 = st.columns(2)
            c1.metric("分镜组数", f"{len(lines)} 组")
            
            if diff == 0:
                c2.metric("偏差值", "0", delta="完美", delta_color="normal")
            elif diff > 0:
                c2.metric("偏差值", f"+{diff}", delta="重复", delta_color="inverse")
            else:
                c2.metric("偏差值", f"{diff}", delta="漏字", delta_color="inverse")

            table_data = []
            for line in lines:
                match = re.match(r'(\d+)[\.、]\s*(.*)', line)
                if match:
                    idx = match.group(1)
                    content = match.group(2)
                    length = len(content)
                    # 评分标准调整：
                    if length > 38: status = "🔴 极长"
                    elif length < 10: status = "⚪ 过碎" # <10字 标记为“过碎”，提醒用户或AI
                    else: status = "🟢 饱满"
                    
                    table_data.append({"序号": idx, "内容": content, "字数": length, "状态": status})
            
            if table_data:
                st.dataframe(
                    pd.DataFrame(table_data), 
                    use_container_width=True, 
                    height=500,
                    column_config={
                        "序号": st.column_config.TextColumn("No.", width="small"),
                        "内容": st.column_config.TextColumn("内容", width="medium"),
                        "字数": st.column_config.NumberColumn("字数", width="small"),
                        "状态": st.column_config.TextColumn("节奏评价", width="medium"),
                    }
                )
