import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# ==========================================
# 🛠️ 核心工具函数库
# ==========================================

def smart_chunk_text(text, max_chars=1000):
    """
    智能分块：寻找最稳固的标点符号（。！？\n）进行切分，
    确保每一块都是完整的段落，防止AI在句子中间截断。
    """
    chunks = []
    while len(text) > max_chars:
        split_index = -1
        for mark in ["\n", "。", "！", "？"]:
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
    # 去除行首的数字和点 (如 "1. " 或 "12、")
    text = re.sub(r'^\d+[\.、]\s*', '', text, flags=re.MULTILINE)
    # 去除所有空白字符，只留汉字标点，用于严格比对
    return "".join(text.split())

def renumber_content(text):
    """
    【新增核心】场记修正逻辑：
    无论用户把文本改成了什么样，强制清洗旧序号，重新按行编号。
    """
    lines = text.split('\n')
    new_lines = []
    counter = 1
    for line in lines:
        stripped = line.strip()
        if not stripped: continue # 跳过空行
        
        # 清除这一行原本可能存在的序号（防呆设计）
        clean_content = re.sub(r'^\d+[\.、]\s*', '', stripped)
        
        # 重新组合
        new_lines.append(f"{counter}. {clean_content}")
        counter += 1
    return "\n".join(new_lines)

# ==========================================
# 🎨 页面配置与初始化
# ==========================================
st.set_page_config(page_title="导演引擎 V12-人机协作版", layout="wide", page_icon="🎬")

# 初始化 Session State (关键：用于存储分镜状态，防止页面刷新后数据丢失)
if 'generated_storyboard' not in st.session_state:
    st.session_state.generated_storyboard = ""
if 'original_text_len' not in st.session_state:
    st.session_state.original_text_len = 0

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V12")
    st.caption("人机协作·动态修正版")
    
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o") # 也可以尝试 deepseek-chat
    
    st.divider()
    st.markdown("### 🕹️ 操作指南")
    st.info("""
    1. 上传文案，点击**启动分镜**。
    2. AI 生成初稿后，在右侧编辑框**手动微调**（换行、合并）。
    3. 点击 **"🔄 格式化并重置序号"**，系统将自动对齐所有数据。
    """)

# ==========================================
# 🖥️ 主界面逻辑
# ==========================================
st.title("🎬 全能文案·电影感分镜系统 (V12)")

uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    # 读取原文
    raw_text = uploaded_file.getvalue().decode("utf-8")
    # 计算纯净长度（用于对比）
    input_stream = "".join(raw_text.split())
    st.session_state.original_text_len = len(input_stream)

    # 顶部数据看板
    st.subheader("📊 视觉逻辑稽核")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{st.session_state.original_text_len} 字")

    # 🚀 启动按钮
    if st.button("🚀 启动 AI 视觉分镜", type="primary"):
        if not api_key:
            st.error("请先在左侧配置 API Key")
        else:
            try:
                # 适配接口地址
                actual_base = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                # 智能分块
                chunks = smart_chunk_text(raw_text)
                status_text = st.empty()
                status_text.info(f"📦 已识别 {len(chunks)} 个剧情块，AI 正在逐块导演中...")
                
                full_result_list = []
                current_shot_idx = 1
                progress_bar = st.progress(0)
                
                for idx, chunk in enumerate(chunks):
                    # Prompt 逻辑保持你满意的版本
                    system_prompt = f"""你是一个解说视频导演。请将文本拆解为“画面镜头”。
                    
【原则】：
1. 主语变了必须换行。
2. 动作和台词分开。
3. 绝对不删减、不增加原文一个字。
4. 这里的数字序号只是临时的，后续会重排，但请你先标上。
5. 必须纯文本输出，不要Markdown代码块。

【起始编号】：{current_shot_idx}
"""
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"处理这段内容：\n{chunk}"}
                        ],
                        temperature=0.1
                    )
                    
                    chunk_res = response.choices[0].message.content.strip()
                    full_result_list.append(chunk_res)
                    
                    # 简单估算下一个编号（虽然最后会重排，但过程要顺畅）
                    last_nums = re.findall(r'(\d+)[\.、]', chunk_res)
                    if last_nums:
                        current_shot_idx = int(last_nums[-1]) + 1
                    
                    progress_bar.progress((idx + 1) / len(chunks))
                
                # 初次生成完成，存入 Session
                raw_combined = "\n".join(full_result_list)
                # 立即进行一次标准化重排，保证格式工整
                st.session_state.generated_storyboard = renumber_content(raw_combined)
                status_text.success("✅ AI 分镜初稿完成！请在下方编辑器进行人工微调。")
                st.rerun() # 重新运行以刷新界面状态

            except Exception as e:
                st.error(f"发生错误：{str(e)}")

    st.divider()

    # ==========================================
    # 📝 核心交互区：人机协作编辑
    # ==========================================
    
    # 只有当有内容时才显示编辑器
    if st.session_state.generated_storyboard:
        
        col_edit, col_analyze = st.columns([1.8, 1.2])
        
        with col_edit:
            st.subheader("🎬 分镜编辑器 (可编辑)")
            st.caption("提示：你可以直接在这里修改文字、按回车切分镜头。修改后点击下方按钮生效。")
            
            # 绑定 session_state 的文本框
            user_edited_text = st.text_area(
                "Storyboard Editor",
                value=st.session_state.generated_storyboard,
                height=600,
                label_visibility="collapsed"
            )
            
            # 🔥 核心功能按钮
            if st.button("🔄 格式化并重置序号 (Refresh)", use_container_width=True):
                # 1. 获取用户刚刚在框里改过的内容
                # 2. 调用重排函数，清洗旧序号，生成新序号
                formatted_text = renumber_content(user_edited_text)
                # 3. 更新状态
                st.session_state.generated_storyboard = formatted_text
                st.success("已根据你的修改重新排列镜头序号！")
                st.rerun() # 强制刷新页面，让右侧表格更新

        # ==========================================
        # 📈 实时分析区 (根据编辑器内容动态更新)
        # ==========================================
        with col_analyze:
            st.subheader("📈 实时数据校验")
            
            # 基于当前 session_state (也就是用户改完后的内容) 进行分析
            current_text = st.session_state.generated_storyboard
            
            # 1. 提取有效行
            lines = [line.strip() for line in current_text.split('\n') if line.strip()]
            shot_count = len(lines)
            
            # 2. 计算处理后字数
            output_pure = get_pure_text(current_text)
            output_len = len(output_pure)
            
            # 3. 计算偏差
            diff = output_len - st.session_state.original_text_len
            
            # 更新顶部 Metrics (利用 container 占位符技巧太麻烦，直接在这里重新展示最稳)
            c1, c2 = st.columns(2)
            c1.metric("当前镜头数", f"{shot_count} 组")
            
            if diff == 0:
                c2.metric("偏差值", "0 字", delta="完美无损")
            else:
                c2.metric("偏差值", f"{diff} 字", delta="存在误差", delta_color="inverse")
                if diff > 0:
                    st.warning(f"⚠️ 内容比原文多了 {diff} 个字 (可能存在重复或AI加戏)")
                else:
                    st.error(f"⚠️ 内容比原文少了 {abs(diff)} 个字 (存在漏字风险)")

            # 4. 生成表格数据
            table_data = []
            for line in lines:
                # 尝试解析 "1. 内容"
                match = re.match(r'(\d+)[\.、]\s*(.*)', line)
                if match:
                    idx = match.group(1)
                    content = match.group(2)
                    length = len(content)
                    status = "🟢 完美" if 20 <= length <= 35 else ("🔴 过长" if length > 35 else "🟡 偏短")
                    
                    table_data.append({
                        "序号": idx,
                        "内容预览": content, # 不截断预览，方便检查
                        "字数": length,
                        "状态": status
                    })
            
            if table_data:
                df = pd.DataFrame(table_data)
                st.dataframe(
                    df, 
                    column_config={
                        "序号": st.column_config.TextColumn("No.", width="small"),
                        "内容预览": st.column_config.TextColumn("文案内容", width="medium"),
                        "字数": st.column_config.NumberColumn("字数"),
                        "状态": st.column_config.TextColumn("时长建议")
                    },
                    height=500,
                    use_container_width=True
                )
            
            # 下载按钮
            st.download_button(
                "💾 下载最终分镜文件 (.txt)",
                data=current_text,
                file_name="final_storyboard.txt",
                mime="text/plain",
                use_container_width=True
            )
