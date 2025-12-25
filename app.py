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

def clean_hallucinations(text):
    """
    🧹 V20 新增：加戏清洗器
    强制删除 AI 可能添加的“镜头、画面、特写”等非原文词汇
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    # 定义必须杀掉的“导演词汇”
    forbidden_patterns = [
        r'^镜头.*?[：:]', r'^画面.*?[：:]', r'^特写.*?[：:]', r'^中景.*?[：:]',
        r'（.*?）', r'\(.*?\)', # 去掉括号里的动作指导
        r'镜头缓缓.*?', r'低声叙述[：:]'
    ]
    
    for line in lines:
        content = line
        # 先分离序号
        match = re.match(r'(\d+[\.、]\s*)(.*)', line)
        if match:
            prefix = match.group(1)
            body = match.group(2)
            
            # 清洗 body 部分
            for pat in forbidden_patterns:
                body = re.sub(pat, '', body).strip()
            
            # 重新组合
            cleaned_lines.append(f"{prefix}{body}")
        else:
            cleaned_lines.append(line)
            
    return "\n".join(cleaned_lines)

def recursive_split(text, threshold=35):
    """
    递归切分工具（阈值调紧至35）
    """
    text = text.strip()
    if not text: return []
    if len(text) <= threshold: return [text]
    
    mid = len(text) // 2
    split_idx = -1
    # 优先找标点
    for i in range(mid, 5, -1):
        if text[i] in ['，', ',', ' ', '；', ';', '。', '！', '？', '：', ':']:
            split_idx = i + 1
            break
            
    if split_idx == -1: split_idx = threshold 
        
    part1 = text[:split_idx].strip()
    part2 = text[split_idx:].strip()
    return recursive_split(part1, threshold) + recursive_split(part2, threshold)

def auto_split_all_lines(full_text, threshold=35):
    lines = full_text.split('\n')
    final_lines = []
    for line in lines:
        clean_line = re.sub(r'^\d+[\.、]\s*', '', line.strip())
        final_lines.extend(recursive_split(clean_line, threshold))
    return renumber_content("\n".join(final_lines))

# ==========================================
# 🎨 页面配置
# ==========================================
st.set_page_config(page_title="导演引擎 V20-严谨纯净版", layout="wide", page_icon="🎬")

if 'generated_storyboard' not in st.session_state:
    st.session_state.generated_storyboard = ""
if 'original_text_pure_len' not in st.session_state:
    st.session_state.original_text_pure_len = 0
if 'editor_key' not in st.session_state:
    st.session_state.editor_key = 0

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V20")
    st.caption("Anti-Hallucination & Logic Isolation")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") 
    
    st.divider()
    st.info("💡 V20 核心：去除了AI的导演权限，禁止加戏；强制分离叙述与对话。")

# ==========================================
# 🖥️ 主界面
# ==========================================
st.title("🎬 全能文案·电影感分镜系统 (V20)")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    pure_raw = get_pure_text(raw_text)
    
    if st.session_state.original_text_pure_len == 0 or len(pure_raw) != st.session_state.original_text_pure_len:
         st.session_state.original_text_pure_len = len(pure_raw)

    st.subheader("📊 视觉逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文汉字数", f"{st.session_state.original_text_pure_len} 字")

    if st.button("🚀 启动 V20 严谨分镜", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                chunks = smart_chunk_text(raw_text)
                
                status = st.empty()
                status.info("执行 V20 净化指令：禁止加戏，台词隔离...")
                
                full_result_list = []
                current_shot_idx = 1
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    # ==========================================
                    # 🔥 V20 Prompt: 严禁加戏 + 强制隔离
                    # ==========================================
                    system_prompt = f"""你是一个没有感情的【文本切分机器】，绝对不是导演，禁止发挥想象力。

【最高禁令 (Forbidden)】：
1. **严禁添加原文没有的词**：禁止出现“镜头推近”、“画面”、“特写”、“旁白”等词汇！
2. **严禁修改原文**：原文是什么字，输出就是什么字。

【切分逻辑 (Isolation)】：
1. **台词必须独立**：
   - 只要出现冒号（：）或引号，说明有人说话，**必须**另起一行！
   - ❌ 错误：男人说道：这画真好
   - ✅ 正确：
     1. 男人说道
     2. 这画真好
     
2. **多事件切分**：
   - 如果一行里包含了【动作 A】和【动作 B】，且总长超过 30 字，请在中间切开。
   - ❌ 错误：床帷顺势落下，卖力的声音不减，所有的目光都聚集在我身上
   - ✅ 正确（事件拆分）：
     1. 床帷顺势落下，卖力的声音不减
     2. 所有的目光都聚集在我身上

3. **叙事合并**：
   - 仅限【同一主语】的连续短动作可以合并。
   - 比如“我是画师，一笔一划...”可以合并。

【起始编号】：{current_shot_idx}
"""
                    clean_chunk = re.sub(r'\s+', '', chunk)
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "system", "content": system_prompt},
                                  {"role": "user", "content": clean_chunk}],
                        temperature=0 # 绝对零度，禁止任何创造性
                    )
                    chunk_res = response.choices[0].message.content.strip()
                    full_result_list.append(chunk_res)
                    
                    last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                    if last_nums: current_shot_idx = int(last_nums[-1]) + 1
                    progress_bar.progress((idx + 1) / len(chunks))
                
                raw_combined = "\n".join(full_result_list)
                
                # 🔥 运行后处理清洗器，杀掉漏网的“镜头词”
                cleaned_text = clean_hallucinations(raw_combined)
                
                st.session_state.generated_storyboard = renumber_content(cleaned_text)
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
                # 阈值调整为 35
                if st.button("✂️ 强力切分 (>35字)", type="primary", use_container_width=True):
                    split_text = auto_split_all_lines(st.session_state.generated_storyboard, threshold=35)
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
            
            # 宽容度处理：只要误差在 20 字以内（可能是标点引起的误判），就算完美
            if abs(diff) < 20:
                c2.metric("偏差值", f"{diff}", delta="正常范围", delta_color="normal")
            else:
                c2.metric("偏差值", f"{diff}", delta="需检查", delta_color="inverse")

            table_data = []
            for line in lines:
                match = re.match(r'(\d+)[\.、]\s*(.*)', line)
                if match:
                    idx = match.group(1)
                    content = match.group(2)
                    length = len(content)
                    
                    if length > 35: status = "🔴 较长" # 阈值降到35
                    elif length < 8: status = "⚪ 短句"
                    else: status = "🟢 完美"
                    
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
                        "状态": st.column_config.TextColumn("评价", width="small"),
                    }
                )
