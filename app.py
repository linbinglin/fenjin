import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# ==========================================
# 🛠️ 核心工具函数库
# ==========================================

def smart_chunk_text(text, max_chars=1200):
    """
    智能分块：保持上下文完整，不从句子中间切断。
    """
    chunks = []
    while len(text) > max_chars:
        split_index = -1
        # 优先在段落或强句号处切分
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
    """用于核对字数：只保留汉字数字"""
    text = re.sub(r'^\d+[\.、]\s*', '', text, flags=re.MULTILINE)
    return re.sub(r'[^\u4e00-\u9fa50-9]', '', text)

def renumber_content(text):
    """清洗旧序号，重新编号"""
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

# ==========================================
# 🎨 页面配置
# ==========================================
st.set_page_config(page_title="导演引擎 V16-语义逻辑版", layout="wide", page_icon="🎬")

if 'generated_storyboard' not in st.session_state:
    st.session_state.generated_storyboard = ""
if 'original_text_pure_len' not in st.session_state:
    st.session_state.original_text_pure_len = 0

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V16")
    st.caption("Semantic Logic Core")
    
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") 
    
    st.divider()
    st.info("💡 V16 更新：移除了暴力切分。使用【少样本学习】教 AI 理解语义气口。")

# ==========================================
# 🖥️ 主界面逻辑
# ==========================================
st.title("🎬 全能文案·电影感分镜系统 (V16)")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    pure_raw = get_pure_text(raw_text)
    st.session_state.original_text_pure_len = len(pure_raw)

    st.subheader("📊 视觉逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文汉字数", f"{len(pure_raw)} 字")

    if st.button("🚀 启动 V16 语义分镜", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                chunks = smart_chunk_text(raw_text)
                status_text = st.empty()
                status_text.info(f"📦 分析语义中... V16 正在寻找画面的【气口】...")
                
                full_result_list = []
                current_shot_idx = 1
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    # ==========================================
                    # 🔥 V16 Prompt: Few-Shot Learning (少样本教学)
                    # ==========================================
                    # 我们不教数学，我们给它看“正确答案”长什么样。
                    system_prompt = f"""你是一个专业的影视分镜导演。你的任务是根据“语义气口”和“视觉节奏”将文案拆分为分镜列表。

【核心心法】：
不要去数多少个字，而是去读这句话的**语义重心**。
1. **一个镜头=一个完整的视觉信息**。
2. **长句必切**：如果一句话包含两个连续的动作，或者包含“转折/因果”关系（通常由逗号连接），且整体较长，**必须**在逗号处切分。
3. **短句合并**：如果两句短话是紧密相连的动作（如：他站起身，走了出去），请合并。

【学习以下案例（Case Study）】：

❌ **错误示范（太长，信息拥挤）**：
1. 第三世得知皇帝又要找人时我俩跪在贵妃旁边再不敢出声，没多久太监却传出旨意

✅ **正确示范（语义切分，有呼吸感）**：
1. 第三世得知皇帝又要找人时，我俩跪在贵妃旁边
2. 再不敢出声，没多久太监却传出旨意

❌ **错误示范（太碎，语义断裂）**：
1. 我看着
2. 母亲在寒风中
3. 瑟瑟发抖

✅ **正确示范（完整画面）**：
1. 我看着母亲在寒风中瑟瑟发抖

【执行规则】：
- 严格保留原文所有汉字，**偏差值必须为0**。
- 仅通过**换行**来调整节奏，不要删改标点。
- 输出格式：数字序号 + 内容。

起始编号：{current_shot_idx}
"""
                    # 预处理：去除换行，把文本压平，让AI自己决定哪里换行
                    clean_chunk = re.sub(r'\s+', '', chunk)

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请处理这段文案：\n{clean_chunk}"}
                        ],
                        temperature=0.1 # 保持低温，确保不乱发挥
                    )
                    
                    chunk_res = response.choices[0].message.content.strip()
                    full_result_list.append(chunk_res)
                    
                    last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                    if last_nums:
                        current_shot_idx = int(last_nums[-1]) + 1
                    
                    progress_bar.progress((idx + 1) / len(chunks))
                
                raw_combined = "\n".join(full_result_list)
                st.session_state.generated_storyboard = renumber_content(raw_combined)
                status_text.success("✅ V16 语义分镜完成！")
                st.rerun()

            except Exception as e:
                st.error(f"Error: {str(e)}")

    st.divider()

    # ==========================================
    # 📝 交互区
    # ==========================================
    if st.session_state.generated_storyboard:
        col_edit, col_analyze = st.columns([1.8, 1.2])
        
        with col_edit:
            st.subheader("🎬 分镜编辑器")
            
            # 我们移除那个暴力的“自动切分”按钮，
            # 只保留“重置序号”，把控制权还给用户。
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
            st.subheader("📈 节奏分析")
            current_text = st.session_state.generated_storyboard
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            
            # 偏差核对
            output_pure = get_pure_text(current_text)
            diff = len(output_pure) - st.session_state.original_text_pure_len
            
            c1, c2 = st.columns(2)
            c1.metric("分镜组数", f"{len(lines)} 组")
            
            if diff == 0:
                c2.metric("偏差值", "0", delta="完美", delta_color="normal")
            else:
                c2.metric("偏差值", f"{diff}", delta="需检查", delta_color="inverse")

            # 表格展示
            table_data = []
            for line in lines:
                match = re.match(r'(\d+)[\.、]\s*(.*)', line)
                if match:
                    idx = match.group(1)
                    content = match.group(2)
                    length = len(content)
                    
                    # 评价逻辑：更宽容，基于语义
                    # 只要不超过 40 字，且不短于 5 字，都算正常
                    if length > 40:
                        status = "🔴 较长 (建议检查)"
                    elif length > 30:
                        status = "🟡 饱满"
                    elif length < 6:
                         # 极短句如果是感叹词是可以的
                        status = "⚪ 短促"
                    else:
                        status = "🟢 适中"
                    
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
                        "
