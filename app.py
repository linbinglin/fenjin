import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 页面配置 ---
st.set_page_config(
    page_title="剪辑引擎 V15 (字幕节奏版)",
    page_icon="✂️",
    layout="wide"
)

# --- CSS ---
st.markdown("""
<style>
    .metric-container { background-color: #f8f9fa; padding: 10px; border-radius: 5px; }
    .stDataFrame { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 剪辑引擎 V15")
    st.caption("核心：纯净断句，拒绝加戏")
    
    api_key = st.text_input("API Key", type="password", placeholder="sk-...")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["gpt-4o", "deepseek-chat", "claude-3-5-sonnet-20240620", "gpt-4-turbo"]
    selected_model = st.selectbox("Model ID", model_options, index=0)
    
    if st.checkbox("自定义模型ID"):
        model_id = st.text_input("输入ID", value=selected_model)
    else:
        model_id = selected_model

    st.divider()
    st.markdown("### ✂️ V15 断句法则")
    st.info("""
    1. **物理阻断**：代码层强制删除AI生成的任何括号备注。
    2. **标点逻辑**：
       - 【。！？】是绝对分界线。
       - 【，】是软分界线，仅在长句时切开。
    3. **时长锚点**：35字 = 5秒红线。
    """)

# --- 核心工具函数 ---

def clean_text_for_ai(text):
    """预处理：去换行，变纯文本流"""
    return text.replace("\n", "").replace("\r", "").strip()

def sanitize_ai_output(text):
    """
    【V15 新增核心功能】
    强制清洗 AI 的幻觉（加戏）。
    去除所有 (xxx)、（xxx）、【xxx】 内容。
    """
    # 去除圆括号、方括号及其内容
    text = re.sub(r'[\(（【\[].*?[\)）】\]]', '', text)
    return text

def normalize_text_for_comparison(text):
    """用于无损比对：忽略标点和空白"""
    punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~“”？，！【】（）、。：；’‘……——"""
    translator = str.maketrans('', '', punctuation)
    # 先清洗可能的AI加戏
    text = sanitize_ai_output(text)
    text = re.sub(r'\d+[.、]', '', text)
    text = re.sub(r'\s+', '', text)
    return text.translate(translator)

def smart_split_text(text, chunk_size=1000):
    sentences = re.split(r'([。！？])', text)
    chunks = []
    current = ""
    temp = []
    for i in range(0, len(sentences)-1, 2):
        temp.append(sentences[i] + sentences[i+1])
    if len(sentences) % 2 == 1:
        temp.append(sentences[-1])
        
    for s in temp:
        if len(current) + len(s) > chunk_size:
            chunks.append(current)
            current = s
        else:
            current += s
    if current:
        chunks.append(current)
    return chunks

def parse_df(full_text):
    lines = full_text.split('\n')
    data = []
    for i, line in enumerate(lines):
        if not line.strip(): continue
        clean_content = re.sub(r'^\d+[.、]\s*', '', line)
        length = len(clean_content)
        
        # 字幕节奏评分
        if length > 35: status = "❌ 读不完 (>35)"
        elif length > 25: status = "⚠️ 稍紧凑 (25-35)"
        elif length < 8: status = "⚡ 短促 (8字内)"
        else: status = "✅ 舒适 (8-25)"
            
        data.append({
            "序号": i+1,
            "分镜文案": clean_content,
            "字数": length,
            "配音节奏": status
        })
    return pd.DataFrame(data)

# --- 主程序 ---
st.title("✂️ 剪辑引擎 V15 (无幻觉版)")

uploaded_file = st.file_uploader("📂 上传文案", type=['txt'])

if uploaded_file:
    raw = uploaded_file.read().decode("utf-8")
    flat_input = clean_text_for_ai(raw)
    input_pure_len = len(normalize_text_for_comparison(flat_input))
    
    chunks = smart_split_text(flat_input)
    
    st.info(f"原文载入：{len(flat_input)} 字符 | {input_pure_len} 有效汉字 | 切分为 {len(chunks)} 块处理")

    st.markdown("---")
    
    if st.button("🚀 开始纯净断句", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            full_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # --- V15 核心指令：字幕逻辑，非导演逻辑 ---
            system_prompt = """
            你是一个专业的【配音字幕断句师】。
            你的任务是将长文案按照“人说话的呼吸节奏”拆分为多行。

            【绝对禁令】：
            1. **严禁加戏**：绝对不要添加任何（场景描述）、（动作指导）、（情绪备注）。只输出原文！
            2. **严禁删减**：原文的一个标点符号都不能少。

            【断句规则】：
            1. **硬切分**：遇到【。！？】必须换行。
            2. **软切分**：遇到【，；】时，如果当前行已超过 20 个字，请在标点处换行。
            3. **长度红线**：
               - 任何一行不得超过 35 字。
               - 如果一句话长达 50 字且没有标点（极少见），请在语义停顿处强制换行。
            4. **防止过碎**：
               - 如果短句（如“他说”）后紧跟标点，且后文属于同一气口，且总长<25字，可以不换行。
            """

            try:
                for i, chunk in enumerate(chunks):
                    status_text.markdown(f"**✂️ 正在剪辑第 {i+1}/{len(chunks)} 块...**")
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文案进行断句处理：\n{chunk}"}
                        ],
                        temperature=0.1 # 极低温，只做逻辑处理
                    )
                    
                    # 获取结果
                    ai_raw_text = response.choices[0].message.content
                    # --- 关键步骤：Python 侧再次清洗 ---
                    # 无论 AI 有没有听话，这里强制把括号内容删掉，防止字数暴涨
                    cleaned_text = sanitize_ai_output(ai_raw_text)
                    
                    full_results.append(cleaned_text)
                    progress_bar.progress((i + 1) / len(chunks))

                # 合成
                combined = "\n".join(full_results)
                final_lines = [line.strip() for line in combined.split('\n') if line.strip()]
                
                # 重建
                final_output_text = ""
                raw_output_content = ""
                for idx, line in enumerate(final_lines):
                    # 清洗序号
                    clean = re.sub(r'^\d+[.、]\s*', '', line)
                    final_output_text += f"{idx+1}. {clean}\n"
                    raw_output_content += clean

                # --- 结果看板 ---
                st.success("✅ 剪辑完成！已自动剔除所有AI脑补的场景描述。")
                
                output_pure_len = len(normalize_text_for_comparison(raw_output_content))
                diff = output_pure_len - input_pure_len
                
                # 统计看板
                st.markdown("### 📊 纯净度核验")
                m1, m2, m3, m4 = st.columns(4)
                
                m1.metric("📄 原文有效字数", f"{input_pure_len}")
                m2.metric("🎬 分镜有效字数", f"{output_pure_len}")
                
                # 偏差值处理
                if diff == 0:
                    delta_msg = "完美无损"
                    d_color = "normal"
                elif diff > 0:
                    delta_msg = f"多 {diff} 字"
                    d_color = "inverse" # 红色
                else:
                    delta_msg = f"少 {abs(diff)} 字"
                    d_color = "inverse"
                
                m3.metric("⚖️ 内容偏差", f"{diff}", delta=delta_msg, delta_color=d_color)
                
                avg_len = round(len(raw_output_content)/len(final_lines), 1)
                m4.metric("平均每行字数", f"{avg_len}", help="20左右为最佳配音节奏")

                if abs(diff) > 10:
                     st.error(f"⚠️ 依然存在 {abs(diff)} 字的偏差。请检查是否 AI 输出了无关的前言或后语。")

                # 内容展示
                c1, c2 = st.columns([1.5, 1])
                
                with c1:
                    st.subheader("📝 分镜结果 (已清洗)")
                    st.text_area("文案预览", value=final_output_text, height=650)
                    st.download_button("📥 下载文案", data=final_output_text, file_name="分镜文案.txt")

                with c2:
                    st.subheader("⏱️ 节奏分析")
                    df = parse_df(final_output_text)
                    st.dataframe(
                        df,
                        column_config={
                            "序号": st.column_config.NumberColumn(width="small"),
                            "分镜文案": st.column_config.TextColumn(width="large"),
                            "字数": st.column_config.ProgressColumn(
                                "阅读时长", 
                                format="%d", 
                                min_value=0, 
                                max_value=40
                            ),
                            "配音节奏": st.column_config.TextColumn(width="medium")
                        },
                        hide_index=True,
                        height=650
                    )

            except Exception as e:
                st.error(f"❌ 出错了: {e}")
