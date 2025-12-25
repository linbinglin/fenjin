import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# ==========================================
# 🛠️ 核心工具函数库
# ==========================================

def smart_chunk_text(text, max_chars=1500):
    """
    智能分块：加大分块阈值，让AI看到更完整的上下文，减少碎片化。
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
    """提取纯文本（去除序号），用于计算字数偏差"""
    text = re.sub(r'^\d+[\.、]\s*', '', text, flags=re.MULTILINE)
    return "".join(text.split())

def renumber_content(text):
    """
    场记修正逻辑：清洗旧序号，重新编号
    """
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
st.set_page_config(page_title="导演引擎 V13-聚合修复版", layout="wide", page_icon="🎬")

if 'generated_storyboard' not in st.session_state:
    st.session_state.generated_storyboard = ""
if 'original_text_len' not in st.session_state:
    st.session_state.original_text_len = 0

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V13")
    st.caption("视觉聚合修复版")
    
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") 
    
    st.divider()
    st.markdown("### 🛠️ 修复日志")
    st.info("""
    **V13 修正逻辑：**
    1. **拒绝碎镜**：强制合并短句，模拟长镜头感。
    2. **满载填充**：单镜头尽量填满 25-35 字。
    3. **严格对账**：偏差值控制算法优化。
    """)

# ==========================================
# 🖥️ 主界面逻辑
# ==========================================
st.title("🎬 全能文案·电影感分镜系统 (V13)")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    # 预处理：把原文本里的换行全部压扁，防止AI被原文格式误导
    flat_raw_text = "".join(raw_text.split()) 
    st.session_state.original_text_len = len(flat_raw_text)

    # 看板
    st.subheader("📊 视觉逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{st.session_state.original_text_len} 字")

    if st.button("🚀 启动 V13 聚合分镜", type="primary"):
        if not api_key:
            st.error("请先在左侧配置 API Key")
        else:
            try:
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                # 分块处理
                chunks = smart_chunk_text(raw_text)
                
                status_text = st.empty()
                status_text.info(f"📦 已识别 {len(chunks)} 个剧情块，正在执行 V13 聚合指令...")
                
                full_result_list = []
                current_shot_idx = 1
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    # ==========================================
                    # 🔥 V13 核心指令 (The Soul)
                    # ==========================================
                    # 这里的指令完全推翻了上一版，强调“合并”和“填满”
                    system_prompt = f"""你是一个追求“长镜头感”的电影导演。请将输入的文案处理为分镜脚本。

【核心指令：视觉聚合】
1. **尽可能合并**：不要把一句话切碎！如果几个连续的动作或描述属于同一个场景且总长不超过 35 字，**必须合并**在同一行。
   - 错误：1. 皇上翻遍后宫 \n 2. 只为找出...
   - 正确：1. 皇上翻遍后宫，只为找出酒后爬龙床的宫女
2. **拒绝短镜头**：除非是极短的惊讶对白（如“什么？”），否则禁止输出少于 10 个字的分镜。
3. **强制换行条件**：
   - 只有当【单行字数超过 35 字】时，才允许在标点处切分。
   - 只有当【明确的角色对话切换】时，才允许换行。
4. **无损还原**：输入了什么字，输出就必须是什么字。严禁增加“镜头1”、“画面：”等任何原文没有的词。

【输出格式】：
纯数字列表，如：
{current_shot_idx}. 第一句完整的话...
{current_shot_idx+1}. 第二句完整的话...
"""
                    # 我们把处理过的“去换行版”文本给AI，逼迫它自己断句
                    # 这一步非常关键，防止AI照抄原文的换行
                    clean_chunk = "".join(chunk.split()) 

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请处理这段文本：\n{clean_chunk}"}
                        ],
                        temperature=0.1 # 极低温度，保证严谨
                    )
                    
                    chunk_res = response.choices[0].message.content.strip()
                    full_result_list.append(chunk_res)
                    
                    # 序号衔接逻辑
                    last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                    if last_nums:
                        current_shot_idx = int(last_nums[-1]) + 1
                    
                    progress_bar.progress((idx + 1) / len(chunks))
                
                # 结果组装
                raw_combined = "\n".join(full_result_list)
                st.session_state.generated_storyboard = renumber_content(raw_combined)
                status_text.success("✅ V13 聚合分镜完成！碎片已大幅减少。")
                st.rerun()

            except Exception as e:
                st.error(f"发生错误：{str(e)}")

    st.divider()

    # 编辑与分析区域
    if st.session_state.generated_storyboard:
        col_edit, col_analyze = st.columns([1.8, 1.2])
        
        with col_edit:
            st.subheader("🎬 分镜编辑器")
            user_edited_text = st.text_area(
                "editor",
                value=st.session_state.generated_storyboard,
                height=600,
                label_visibility="collapsed"
            )
            
            if st.button("🔄 格式化并重置序号", use_container_width=True):
                formatted_text = renumber_content(user_edited_text)
                st.session_state.generated_storyboard = formatted_text
                st.rerun()

        with col_analyze:
            st.subheader("📈 数据校验")
            current_text = st.session_state.generated_storyboard
            
            # 计算指标
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            output_pure = get_pure_text(current_text)
            output_len = len(output_pure)
            diff = output_len - st.session_state.original_text_len
            
            c1, c2 = st.columns(2)
            c1.metric("当前镜头数", f"{len(lines)} 组")
            
            # 偏差值颜色逻辑
            if diff == 0:
                c2.metric("偏差值", "0 字", delta="完美", delta_color="normal")
            else:
                c2.metric("偏差值", f"{diff} 字", delta="异常", delta_color="inverse")
                st.warning("提示：如果偏差值过大，请检查编辑器底部是否有AI生成的总结语或多余空行，手动删除即可。")

            # 表格分析
            table_data = []
            for line in lines:
                match = re.match(r'(\d+)[\.、]\s*(.*)', line)
                if match:
                    idx = match.group(1)
                    content = match.group(2)
                    length = len(content)
                    # 只有极短的才警告
                    status = "🟢 优秀" if 15 <= length <= 38 else ("🔴 过长" if length > 38 else "🟡 过碎")
                    
                    table_data.append({
                        "序号": idx,
                        "内容": content,
                        "字数": length,
                        "评价": status
                    })
            
            if table_data:
                st.dataframe(pd.DataFrame(table_data), use_container_width=True, height=500)
