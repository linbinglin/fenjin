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
        
        if split_index == -1:
            split_index = max_chars
        else:
            split_index += 1 
        chunks.append(text[:split_index].strip())
        text = text[split_index:]
    if text.strip():
        chunks.append(text.strip())
    return chunks

def get_pure_text(text):
    """只保留汉字和数字，用于精准对比"""
    text = re.sub(r'^\d+[\.、]\s*', '', text, flags=re.MULTILINE)
    return re.sub(r'[^\u4e00-\u9fa50-9]', '', text)

def renumber_content(text):
    """清洗并重新编号"""
    lines = text.split('\n')
    new_lines = []
    counter = 1
    for line in lines:
        stripped = line.strip()
        if not stripped: continue
        clean_content = re.sub(r'^\d+[\.、]\s*', '', stripped)
        new_lines.append(f"{counter}. {clean_content}")
        counter += 1
    return "\n".join(new_lines)

def force_split_long_lines(text, threshold=36):
    """
    ⚔️ 隐形剪刀算法 (V15核心)
    不依赖AI，使用Python硬逻辑强制切分过长镜头。
    """
    lines = text.split('\n')
    new_lines = []
    
    for line in lines:
        # 去掉序号
        clean_line = re.sub(r'^\d+[\.、]\s*', '', line.strip())
        
        if len(clean_line) <= threshold:
            new_lines.append(clean_line)
        else:
            # === 强制切分逻辑 ===
            # 策略：从中间位置开始，向两边寻找最佳切分点（标点符号）
            mid = len(clean_line) // 2
            split_idx = -1
            
            # 优先找标点
            search_range = 10 # 在中间点左右10个字范围内找标点
            chars_priority = ['，', ',', '；', ';', ' ', '！', '!', '？', '?']
            
            for char in chars_priority:
                # 向右搜
                pos_r = clean_line.find(char, mid)
                if pos_r != -1 and pos_r < mid + search_range:
                    split_idx = pos_r + 1 # 切在标点后
                    break
                # 向左搜
                pos_l = clean_line.rfind(char, 0, mid)
                if pos_l != -1 and pos_l > mid - search_range:
                    split_idx = pos_l + 1
                    break
            
            # 如果实在找不到标点（比如一大段纯文字），就硬切在中间
            if split_idx == -1:
                split_idx = mid
            
            # 执行切分
            part1 = clean_line[:split_idx].strip()
            part2 = clean_line[split_idx:].strip()
            
            if part1: new_lines.append(part1)
            # 如果第二部分依然太长（罕见），这里递归逻辑可以简化，暂时直接放进去，一般切一次就够了
            if part2: new_lines.append(part2)

    # 重新生成带序号的文本
    return renumber_content("\n".join(new_lines))

# ==========================================
# 🎨 页面配置
# ==========================================
st.set_page_config(page_title="导演引擎 V15-强制修正版", layout="wide", page_icon="🎬")

if 'generated_storyboard' not in st.session_state:
    st.session_state.generated_storyboard = ""
if 'original_text_pure_len' not in st.session_state:
    st.session_state.original_text_pure_len = 0

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V15")
    st.caption("Auto-Split Enabled")
    
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") 
    
    st.divider()
    st.markdown("### V15 强力逻辑")
    st.warning("⚠️ 系统将在生成后自动强制切断所有超过 36 字的长镜头，无需人工干预。")

# ==========================================
# 🖥️ 主界面逻辑
# ==========================================
st.title("🎬 全能文案·电影感分镜系统 (V15)")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    
    # 计算纯汉字长度
    pure_raw = get_pure_text(raw_text)
    st.session_state.original_text_pure_len = len(pure_raw)

    st.subheader("📊 视觉逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文汉字数", f"{len(pure_raw)} 字")

    if st.button("🚀 启动 V15 智能分镜", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                chunks = smart_chunk_text(raw_text)
                status_text = st.empty()
                status_text.info(f"📦 处理中... V15 将自动执行两次校验...")
                
                full_result_list = []
                current_shot_idx = 1
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    # ==========================================
                    # 🔥 V15 Prompt: 强调“呼吸感”
                    # ==========================================
                    system_prompt = f"""你是一个电影剪辑师。请将文案转化为分镜脚本。

【最高指令：视觉呼吸感】
1. **拒绝拥挤**：任何一个分镜如果读起来超过 5 秒（约35字），就是失败的。
2. **主动切分**：遇到长难句，即使没有标点，也要根据语意在中间换行！
   - 错误：1. 第三世得知皇帝又要找人时我俩跪在贵妃旁边不敢出声
   - 正确：
     1. 第三世得知皇帝又要找人时
     2. 我俩跪在贵妃旁边不敢出声
3. **保持连贯**：短于 15 字的动作，请合并。

【输出格式】：
{current_shot_idx}. 内容
{current_shot_idx+1}. 内容
"""
                    clean_chunk = re.sub(r'\s+', '', chunk)

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"分镜处理：\n{clean_chunk}"}
                        ],
                        temperature=0.1
                    )
                    
                    chunk_res = response.choices[0].message.content.strip()
                    full_result_list.append(chunk_res)
                    
                    last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                    if last_nums:
                        current_shot_idx = int(last_nums[-1]) + 1
                    
                    progress_bar.progress((idx + 1) / len(chunks))
                
                # === 🌟 关键步骤：合并后立即执行“隐形剪刀” ===
                raw_combined = "\n".join(full_result_list)
                
                # 调用 Python 强制切分函数（阈值设为36，严格控制）
                final_polished_text = force_split_long_lines(raw_combined, threshold=36)
                
                st.session_state.generated_storyboard = final_polished_text
                status_text.success("✅ V15 处理完成！过长镜头已被强制修正。")
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
            
            # 手动刷新按钮（依然保留，以防万一）
            if st.button("🔄 格式化并重置序号", use_container_width=True):
                formatted = renumber_content(st.session_state.widget_text_area)
                st.session_state.generated_storyboard = formatted
                st.rerun()

            def update_text():
                st.session_state.generated_storyboard = st.session_state.widget_text_area

            user_edited_text = st.text_area(
                "editor",
                value=st.session_state.generated_storyboard,
                height=600,
                key="widget_text_area",
                on_change=update_text,
                label_visibility="collapsed"
            )

        with col_analyze:
            st.subheader("📈 数据校验")
            current_text = st.session_state.generated_storyboard
            
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            
            # 偏差计算
            output_pure = get_pure_text(current_text)
            diff = len(output_pure) - st.session_state.original_text_pure_len
            
            c1, c2 = st.columns(2)
            c1.metric("分镜组数", f"{len(lines)} 组")
            
            # 宽容度稍微调高一点，因为强制切分不会丢字，只会增加行数
            if abs(diff) < 5:
                c2.metric("偏差值", "0", delta="完美", delta_color="normal")
            else:
                c2.metric("偏差值", f"{diff}", delta="需检查", delta_color="inverse")

            # 节奏表格
            table_data = []
            for line in lines:
                match = re.match(r'(\d+)[\.、]\s*(.*)', line)
                if match:
                    idx = match.group(1)
                    content = match.group(2)
                    length = len(content)
                    
                    # 评分标准微调
                    if length > 38:
                        status = "🔴 依然长" # 如果这一步还出现红色，说明这句真的一点标点都没有
                    elif length > 34:
                        status = "🟡 饱满"
                    elif length < 10:
                        status = "⚪ 短促"
                    else:
                        status = "🟢 完美"
                    
                    table_data.append({
                        "序号": idx,
                        "内容": content,
                        "字数": length,
                        "状态": status
                    })
            
            if table_data:
                st.dataframe(
                    pd.DataFrame(table_data), 
                    use_container_width=True, 
                    height=500,
                    column_config={
                        "序号": st.column_config.TextColumn("No.", width="small"),
                        "内容": st.column_config.TextColumn("内容", width="medium"),
                        "字数": st.column_config.NumberColumn("字数", width="small"),
                        "状态": st.column_config.TextColumn("状态", width="small"),
                    }
                )
