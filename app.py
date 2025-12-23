import streamlit as st
from openai import OpenAI
import re
import pandas as pd
import math

# --- 页面基础配置 ---
st.set_page_config(
    page_title="全能文案·电影感分镜系统 (V11)",
    page_icon="🎬",
    layout="wide"
)

# --- 自定义 CSS (为了还原截图中的专业感) ---
st.markdown("""
<style>
    .metric-container {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .stDataFrame { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏：参数配置 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V11")
    
    api_key = st.text_input("API Key", type="password", placeholder="sk-xxxxxxxx")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    
    # 模型选择
    model_options = ["gpt-4o", "deepseek-chat", "claude-3-5-sonnet-20240620", "grok-beta", "gpt-3.5-turbo"]
    selected_model = st.selectbox("Model ID", model_options, index=0)
    
    if st.checkbox("手动输入模型ID"):
        model_id = st.text_input("自定义ID", value=selected_model)
    else:
        model_id = selected_model

    st.info("""
    **📋 V11 视觉切分准则：**
    1. **主语即镜头**：人称切换必须切镜。
    2. **动作即分镜**：动作完成必须切镜。
    3. **硬性35字**：单行禁止超过35字。
    """)

# --- 核心工具函数 ---

def clean_text_for_ai(text):
    """预处理：去除换行，变成纯文本流"""
    return text.replace("\n", "").replace("\r", "").strip()

def smart_split_text(text, chunk_size=800):
    """
    智能分段：按句号/标点切分，避免截断句子。
    将长文本切分为多个 chunk，每个约 chunk_size 字。
    """
    chunks = []
    current_chunk = ""
    
    # 简单的按句切分逻辑
    sentences = re.split(r'([。！？])', text)
    
    # 重新组合
    temp_sentences = []
    for i in range(0, len(sentences)-1, 2):
        temp_sentences.append(sentences[i] + sentences[i+1])
    if len(sentences) % 2 == 1:
        temp_sentences.append(sentences[-1])
        
    for sentence in temp_sentences:
        if len(current_chunk) + len(sentence) > chunk_size:
            chunks.append(current_chunk)
            current_chunk = sentence
        else:
            current_chunk += sentence
            
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def parse_storyboard_to_df(full_text):
    """
    将分镜文本解析为 DataFrame，用于右侧表格展示
    """
    lines = full_text.strip().split('\n')
    data = []
    index_counter = 1
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # 去除开头的序号 (比如 "1. xxx" -> "xxx")
        content = re.sub(r'^\d+[.、]\s*', '', line)
        
        length = len(content)
        status = "✅ 理想" if length <= 35 else "⚠️ 过长"
        
        data.append({
            "序号": index_counter,
            "内容预览": content,
            "长度": length,
            "状态": status
        })
        index_counter += 1
        
    return pd.DataFrame(data)

def get_system_prompt():
    return """
    你是一个专业的电影解说分镜师。
    任务：将提供的文本按视觉逻辑拆解为分镜脚本。
    
    【核心规则】：
    1. **绝对忠实**：严禁删减原文，严禁增加原文没有的词。
    2. **分镜逻辑**：
       - 角色切换 -> 换行
       - 场景/时间切换 -> 换行
       - 动作/画面改变 -> 换行
    3. **长度风控**：
       - 每一行代表约5秒画面。
       - **强制**：如果一句话超过35个字，必须在语义连贯处强制换行。
    
    【输出格式】：
    不输出任何前言后语，只输出分镜内容，每行一句。
    （不需要你自己标数字序号，直接输出文本行即可，系统会自动编号）
    """

# --- 主界面逻辑 ---

st.title("🎬 全能文案·电影感分镜系统 (V11)")

# 1. 上传区域
uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file:
    raw_content = uploaded_file.read().decode("utf-8")
    flat_content = clean_text_for_ai(raw_content)
    input_len = len(flat_content)
    
    # 计算需要分多少段 (模仿图2)
    chunks = smart_split_text(flat_content, chunk_size=800) # 800字一段，防止AI过载
    total_chunks = len(chunks)

    # 顶部仪表盘 (静态)
    st.markdown("### 📊 视觉逻辑稽核面板")
    st.metric("原文总字数", f"{input_len} 字")
    
    if total_chunks > 1:
        st.info(f"📁 已识别 {total_chunks} 个独立剧情块，正在进行视觉单元规划...")
    
    # 2. 启动按钮
    if st.button("🚀 启动视觉无损分镜", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            full_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # --- 循环处理每个块 (Chunking) ---
                for i, chunk in enumerate(chunks):
                    current_step = i + 1
                    status_text.text(f"正在规划第 {current_step}/{total_chunks} 块镜头... ({len(chunk)}字)")
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": get_system_prompt()},
                            {"role": "user", "content": f"处理以下文本：\n{chunk}"}
                        ],
                        temperature=0.1
                    )
                    
                    # 获取结果并清理
                    chunk_res = response.choices[0].message.content
                    full_results.append(chunk_res)
                    
                    # 更新进度条
                    progress_bar.progress(current_step / total_chunks)

                status_text.text("✅ 所有镜头规划完毕，正在进行最终合成...")
                
                # --- 合成最终结果 ---
                # 将所有段落拼合，并统一按行分割
                combined_text = "\n".join(full_results)
                # 清洗空行
                final_lines = [line.strip() for line in combined_text.split('\n') if line.strip()]
                
                # 重新加上序号 (1. 2. 3...)
                numbered_text = ""
                raw_text_only = "" # 用于计算生成总字数
                for idx, line in enumerate(final_lines):
                    clean_line = re.sub(r'^\d+[.、]\s*', '', line) # 再次清洗以防AI自己加了序号
                    numbered_text += f"{idx+1}. {clean_line}\n"
                    raw_text_only += clean_line

                # --- 结果展示页面 (模仿图3) ---
                st.markdown("---")
                
                # 计算统计数据
                output_len = len(raw_text_only)
                deviation = output_len - input_len
                scene_count = len(final_lines)
                avg_len = round(output_len / scene_count, 1) if scene_count > 0 else 0

                # 顶部统计栏 (Columns)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("原文总字数", f"{input_len}")
                m2.metric("生成分镜总数", f"{scene_count} 组")
                m3.metric("处理后总字数", f"{output_len}")
                m4.metric("偏差值", f"{deviation} 字", 
                          delta_color="off" if deviation == 0 else "inverse")
                
                if abs(deviation) > 10:
                    st.warning(f"⚠️ 偏差：{deviation} 字。正数为重复/脑补，负数为漏字。")

                # --- 双栏布局：左侧编辑器，右侧分析表 ---
                col_left, col_right = st.columns([1.8, 1.2]) # 左宽右窄
                
                with col_left:
                    st.subheader("🎬 视觉分镜编辑器 (无损还原)")
                    # Text Area用于复制
                    st.text_area("分镜正文", value=numbered_text, height=600)
                    
                    st.download_button(
                        "💾 下载最终分镜稿",
                        data=numbered_text,
                        file_name="分镜脚本.txt"
                    )

                with col_right:
                    st.subheader("📊 实时视觉节奏分析")
                    # 生成 DataFrame
                    df = parse_storyboard_to_df(numbered_text)
                    
                    # 使用 Streamlit 的 Column Config 美化表格
                    st.dataframe(
                        df,
                        column_config={
                            "序号": st.column_config.NumberColumn("序号", width="small"),
                            "内容预览": st.column_config.TextColumn("内容预览", width="large"),
                            "长度": st.column_config.ProgressColumn(
                                "长度", 
                                format="%d", 
                                min_value=0, 
                                max_value=50, # 进度条最大值设为50，方便看35的界限
                            ),
                            "状态": st.column_config.TextColumn("状态", width="small"),
                        },
                        hide_index=True,
                        height=600
                    )
                    
                    st.info(f"平均每镜停留：{avg_len} 字 (约 {round(avg_len/7, 1)} 秒)")

            except Exception as e:
                st.error(f"处理过程中发生错误: {e}")
