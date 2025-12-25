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
    """只保留汉字和数字，用于精准对比，忽略标点差异"""
    # 1. 去掉序号 "1. "
    text = re.sub(r'^\d+[\.、]\s*', '', text, flags=re.MULTILINE)
    # 2. 只留中文字符和数字
    return re.sub(r'[^\u4e00-\u9fa50-9]', '', text)

def renumber_content(text):
    """标准化重排"""
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
    ⚔️ 递归强力切分 (Nuclear Option)
    只要长度 > threshold，就一直切，直到切碎为止。
    """
    # 去除首尾空白
    text = text.strip()
    if not text: return []
    
    # 如果达标，直接返回
    if len(text) <= threshold:
        return [text]
    
    # === 需要切分 ===
    # 寻找最佳切分点：优先找标点，找不到就硬切
    # 搜索范围：从中间向左找，避免切在太靠后的位置
    mid = len(text) // 2
    split_idx = -1
    
    # 优先找标点 (逗号, 空格, 分号)
    # 我们只向左搜，确保第一句尽量完整但不超长
    for i in range(mid, 5, -1): # 从中间往回倒数到第5个字
        if text[i] in ['，', ',', ' ', '；', ';', '。', '！', '？']:
            split_idx = i + 1 # 切在标点后
            break
            
    # 如果找不到标点，为了防止单行过长，强制在 threshold 处切断
    if split_idx == -1:
        split_idx = threshold 
        
    part1 = text[:split_idx].strip()
    part2 = text[split_idx:].strip()
    
    # 递归调用：对切出来的两部分继续检查
    # 这就是“剪切率百分百”的关键
    return recursive_split(part1, threshold) + recursive_split(part2, threshold)

def auto_split_all_lines(full_text, threshold=38):
    """应用递归切分到全文"""
    lines = full_text.split('\n')
    final_lines = []
    
    for line in lines:
        # 去掉序号
        clean_line = re.sub(r'^\d+[\.、]\s*', '', line.strip())
        # 递归切分当前行
        split_segments = recursive_split(clean_line, threshold)
        final_lines.extend(split_segments)
        
    return renumber_content("\n".join(final_lines))

# ==========================================
# 🎨 页面配置
# ==========================================
st.set_page_config(page_title="导演引擎 V17-递归修复版", layout="wide", page_icon="🎬")

# Session State 初始化
if 'generated_storyboard' not in st.session_state:
    st.session_state.generated_storyboard = ""
if 'original_text_pure_len' not in st.session_state:
    st.session_state.original_text_pure_len = 0
# 新增一个 key 用于强制刷新 Text Area
if 'editor_key' not in st.session_state:
    st.session_state.editor_key = 0 

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V17")
    st.caption("Recursive Splitting Engine")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") 

# ==========================================
# 🖥️ 主界面
# ==========================================
st.title("🎬 全能文案·电影感分镜系统 (V17)")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    pure_raw = get_pure_text(raw_text)
    
    # 只有当是新文件时才更新原文长度（防止切分后长度变化导致误判）
    if st.session_state.original_text_pure_len == 0 or len(pure_raw) != st.session_state.original_text_pure_len:
         st.session_state.original_text_pure_len = len(pure_raw)

    st.subheader("📊 视觉逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文汉字数", f"{st.session_state.original_text_pure_len} 字")

    if st.button("🚀 启动 V17 智能分镜", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                chunks = smart_chunk_text(raw_text)
                st.toast(f"开始处理 {len(chunks)} 个块...")
                
                full_result_list = []
                current_shot_idx = 1
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    # Prompt 保持 V16 的语义逻辑
                    system_prompt = f"""你是一个专业分镜导演。任务：将文案按【视觉气口】切分。
规则：
1. 语义完整的长句，请在逗号处换行。
2. 保持原文所有汉字。
3. 起始编号：{current_shot_idx}
"""
                    clean_chunk = re.sub(r'\s+', '', chunk)
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "system", "content": system_prompt},
                                  {"role": "user", "content": clean_chunk}],
                        temperature=0.1
                    )
                    chunk_res = response.choices[0].message.content.strip()
                    full_result_list.append(chunk_res)
                    
                    last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                    if last_nums: current_shot_idx = int(last_nums[-1]) + 1
                    progress_bar.progress((idx + 1) / len(chunks))
                
                # 初始生成
                raw_combined = "\n".join(full_result_list)
                st.session_state.generated_storyboard = renumber_content(raw_combined)
                # 更新 key 以强制重绘编辑器
                st.session_state.editor_key += 1 
                st.rerun()

            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.divider()

    # ==========================================
    # 📝 核心编辑器
    # ==========================================
    if st.session_state.generated_storyboard:
        col_edit, col_analyze = st.columns([1.8, 1.2])
        
        with col_edit:
            st.subheader("🎬 分镜编辑器")
            
            # --- 按钮区 ---
            b1, b2 = st.columns([1, 1])
            with b1:
                if st.button("🔄 仅重置序号", use_container_width=True):
                    formatted = renumber_content(st.session_state.generated_storyboard)
                    st.session_state.generated_storyboard = formatted
                    st.session_state.editor_key += 1 # 强制刷新
                    st.rerun()
            
            with b2:
                # 🔥 V17 修复版切分按钮
                if st.button("✂️ 强力切分 (>38字)", type="primary", use_container_width=True):
                    # 1. 执行递归切分
                    split_text = auto_split_all_lines(st.session_state.generated_storyboard, threshold=38)
                    # 2. 更新数据
                    st.session_state.generated_storyboard = split_text
                    # 3. 关键：更改 widget key，强制 Streamlit 丢弃旧组件，渲染新组件
                    st.session_state.editor_key += 1 
                    st.rerun()

            # --- 文本框 ---
            # 这里的 Key 是动态的，每次点击按钮都会变，确保 UI 必定更新
            current_val = st.text_area(
                "editor",
                value=st.session_state.generated_storyboard,
                height=600,
                key=f"editor_{st.session_state.editor_key}", 
                label_visibility="collapsed"
            )
            
            # 监听手动修改：当用户打字时，手动同步回 session_state
            if current_val != st.session_state.generated_storyboard:
                st.session_state.generated_storyboard = current_val

        with col_analyze:
            st.subheader("📈 数据校验")
            current_text = st.session_state.generated_storyboard
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            
            # 偏差计算
            output_pure = get_pure_text(current_text)
            diff = len(output_pure) - st.session_state.original_text_pure_len
            
            c1, c2 = st.columns(2)
            c1.metric("分镜组数", f"{len(lines)} 组")
            
            # 偏差逻辑
            if diff == 0:
                c2.metric("偏差值", "0", delta="完美", delta_color="normal")
            elif diff > 0:
                c2.metric("偏差值", f"+{diff}", delta="重复/增生", delta_color="inverse")
            else:
                c2.metric("偏差值", f"{diff}", delta="漏字", delta_color="inverse")

            # 表格
            table_data = []
            for line in lines:
                match = re.match(r'(\d+)[\.、]\s*(.*)', line)
                if match:
                    idx = match.group(1)
                    content = match.group(2)
                    length = len(content)
                    status = "🔴 极长" if length > 38 else ("🟢 完美" if length >= 5 else "⚪ 短促")
                    table_data.append({"序号": idx, "内容": content, "字数": length, "状态": status})
            
            if table_data:
                st.dataframe(pd.DataFrame(table_data), use_container_width=True, height=500)
