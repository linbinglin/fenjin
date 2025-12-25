import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# ==========================================
# 🛠️ 核心工具函数库
# ==========================================

def smart_chunk_text(text, max_chars=1200):
    """
    智能分块：适中的分块大小，保证上下文连贯
    """
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
    """提取纯汉字文本，用于最严格的偏差计算"""
    # 去除序号，去除标点，去除空格，只算汉字
    text = re.sub(r'^\d+[\.、]\s*', '', text, flags=re.MULTILINE)
    # 仅保留汉字和数字，忽略标点符号带来的差异
    return re.sub(r'[^\u4e00-\u9fa50-9]', '', text)

def renumber_content(text):
    """标准清洗与重排"""
    lines = text.split('\n')
    new_lines = []
    counter = 1
    for line in lines:
        stripped = line.strip()
        if not stripped: continue
        # 去掉旧序号
        clean_content = re.sub(r'^\d+[\.、]\s*', '', stripped)
        new_lines.append(f"{counter}. {clean_content}")
        counter += 1
    return "\n".join(new_lines)

def auto_split_long_lines(text, threshold=38):
    """
    🔪 Python 级强力修剪工具
    如果某一行超过 threshold 字，强制在中间的标点符号处切开。
    """
    lines = text.split('\n')
    new_lines = []
    
    for line in lines:
        # 先清洗序号
        clean_line = re.sub(r'^\d+[\.、]\s*', '', line.strip())
        
        if len(clean_line) <= threshold:
            new_lines.append(clean_line)
        else:
            # 需要切分。寻找中间位置的标点
            # 优先找逗号，其次找空格
            split_found = False
            # 从字符串中间向两边搜索最佳切分点
            mid = len(clean_line) // 2
            # 搜索范围：中间向两边扩散
            for offset in range(mid):
                # 向右搜
                if clean_line[mid + offset] in ['，', ',', ' ', '；']:
                    p1 = clean_line[:mid + offset + 1] # 包含标点
                    p2 = clean_line[mid + offset + 1:]
                    new_lines.append(p1)
                    new_lines.append(p2)
                    split_found = True
                    break
                # 向左搜
                if clean_line[mid - offset] in ['，', ',', ' ', '；']:
                    p1 = clean_line[:mid - offset + 1]
                    p2 = clean_line[mid - offset + 1:]
                    new_lines.append(p1)
                    new_lines.append(p2)
                    split_found = True
                    break
            
            if not split_found:
                # 实在没标点，硬切（虽然罕见）
                new_lines.append(clean_line)
                
    # 切分完后全是没序号的列表，重新编号返回
    return renumber_content("\n".join(new_lines))

# ==========================================
# 🎨 页面配置
# ==========================================
st.set_page_config(page_title="导演引擎 V14-节奏平衡版", layout="wide", page_icon="🎬")

if 'generated_storyboard' not in st.session_state:
    st.session_state.generated_storyboard = ""
if 'original_text_pure_len' not in st.session_state:
    st.session_state.original_text_pure_len = 0

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V14")
    st.caption("视觉节奏修正版")
    
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") 
    
    st.divider()
    st.info("💡 V14 更新：增加了自动修剪功能，防止出现 60 字的长镜头。")

# ==========================================
# 🖥️ 主界面逻辑
# ==========================================
st.title("🎬 全能文案·电影感分镜系统 (V14)")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    
    # 计算纯汉字长度（排除标点影响）
    pure_raw = get_pure_text(raw_text)
    st.session_state.original_text_pure_len = len(pure_raw)

    # 看板
    st.subheader("📊 视觉逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文汉字数", f"{len(pure_raw)} 字")

    if st.button("🚀 启动 V14 智能分镜", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                chunks = smart_chunk_text(raw_text)
                
                status_text = st.empty()
                status_text.info(f"📦 已识别 {len(chunks)} 个剧情块，正在执行 V14 节奏指令...")
                
                full_result_list = []
                current_shot_idx = 1
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    # ==========================================
                    # 🔥 V14 核心指令：黄金中庸之道
                    # ==========================================
                    system_prompt = f"""你是一个对画面节奏极其敏感的电影剪辑师。请将文案处理为分镜。

【核心节奏法则】：
1. **聚合原则**：连贯的动作请合并，不要把“他站起来”和“他走过去”分成两行。
2. **熔断原则 (至关重要)**：
   - 理想单镜长度：**20-35 字**。
   - **绝对禁止**超过 45 字的长镜头！
   - 如果一句话很长（包含多个逗号），必须在中间的逗号处切开，另起一行。
   - 例子错误：10. 第三世得知皇帝又要找人时我俩跪在贵妃旁边再不敢出声... (太长！)
   - 例子正确：
     10. 第三世得知皇帝又要找人时，我俩跪在贵妃旁边
     11. 再不敢出声，没多久太监却传出旨意

3. **标点保留**：请务必保留原文的标点符号（逗号），不要把它们删掉！这对于断句至关重要。
4. **无损还原**：不要改字，不要删字。

【输出格式】：
{current_shot_idx}. 内容...
{current_shot_idx+1}. 内容...
"""
                    # V14 调整：不再完全压扁文本，保留部分标点结构给AI参考
                    clean_chunk = re.sub(r'\s+', '', chunk) # 去除空格换行，但保留标点

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
                    
                    # 序号估算
                    last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                    if last_nums:
                        current_shot_idx = int(last_nums[-1]) + 1
                    
                    progress_bar.progress((idx + 1) / len(chunks))
                
                raw_combined = "\n".join(full_result_list)
                st.session_state.generated_storyboard = renumber_content(raw_combined)
                status_text.success("✅ V14 分镜完成！节奏已优化。")
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
            
            # --- V14 新增工具栏 ---
            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                # 原有的重排按钮
                if st.button("🔄 仅重置序号 (Refresh)", use_container_width=True):
                    formatted_text = renumber_content(st.session_state.generated_storyboard)
                    st.session_state.generated_storyboard = formatted_text
                    st.rerun()
            with btn_col2:
                # 🔥 新增：强力修剪按钮
                if st.button("🔪 自动切分过长分镜 (>38字)", type="secondary", use_container_width=True):
                    # 调用 Python 函数强制切分
                    split_text = auto_split_long_lines(st.session_state.generated_storyboard, threshold=38)
                    st.session_state.generated_storyboard = split_text
                    st.success("已自动将过长的分镜切分！")
                    st.rerun()
            # ---------------------

            # 绑定 Text Area 到 session_state，并监听 on_change
            # 这样用户手动修改也会被保存
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
            
            # 指标计算
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            
            # 偏差值计算 (使用 V14 更科学的纯汉字比对)
            output_pure = get_pure_text(current_text)
            diff = len(output_pure) - st.session_state.original_text_pure_len
            
            c1, c2 = st.columns(2)
            c1.metric("分镜组数", f"{len(lines)} 组")
            
            if diff == 0:
                c2.metric("偏差值", "0", delta="完美", delta_color="normal")
            elif abs(diff) < 10: # 允许微小误差
                 c2.metric("偏差值", f"{diff}", delta="正常范围", delta_color="off")
            else:
                c2.metric("偏差值", f"{diff}", delta="异常", delta_color="inverse")
                if diff > 0:
                    st.warning(f"AI 似乎多生成了 {diff} 个字，请检查是否有重复段落。")
                else:
                    st.warning(f"AI 似乎遗漏了 {abs(diff)} 个字。")

            # 节奏表格
            table_data = []
            for line in lines:
                match = re.match(r'(\d+)[\.、]\s*(.*)', line)
                if match:
                    idx = match.group(1)
                    content = match.group(2)
                    length = len(content)
                    
                    # 评分逻辑
                    if length > 38:
                        status = "🔴 极长 (建议切分)"
                    elif length > 30:
                        status = "🟡 略长"
                    elif length < 8:
                        status = "⚪ 过短"
                    else:
                        status = "🟢 完美"
                    
                    table_data.append({
                        "序号": idx,
                        "内容": content,
                        "字数": length,
                        "评价": status
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
                        "评价": st.column_config.TextColumn("状态", width="small"),
                    }
                )
