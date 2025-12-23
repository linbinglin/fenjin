import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 页面配置 ---
st.set_page_config(
    page_title="导演引擎 V16 (动作回归版)",
    page_icon="🎬",
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
    st.header("⚙️ 导演引擎 V16")
    st.caption("回归初心：角色·场景·动作")
    
    api_key = st.text_input("API Key", type="password", placeholder="sk-...")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["gpt-4o", "deepseek-chat", "claude-3-5-sonnet-20240620", "gpt-4-turbo"]
    selected_model = st.selectbox("Model ID", model_options, index=0)
    
    if st.checkbox("自定义模型ID"):
        model_id = st.text_input("输入ID", value=selected_model)
    else:
        model_id = selected_model

    st.divider()
    st.markdown("### 🎬 V16 分镜原则")
    st.info("""
    **回归最原始的 3 大切分逻辑：**
    1. 👤 **角色切换**：A说完B说 -> 切！
    2. 🌍 **场景切换**：室内转室外/白天转黑夜 -> 切！
    3. 🏃 **动作改变**：推倒 -> 画画 -> 穿衣。动作变了就必须切，哪怕只有3个字！
    """)

# --- 核心工具函数 ---

def clean_text_for_ai(text):
    """预处理：去换行，变纯文本流"""
    return text.replace("\n", "").replace("\r", "").strip()

def sanitize_ai_output(text):
    """
    【强制清洗】
    不管Prompt怎么强调，防止AI脑补画面描述。
    强制删除所有括号内容。
    """
    text = re.sub(r'[\(（【\[].*?[\)）】\]]', '', text)
    return text

def normalize_text_for_comparison(text):
    """用于无损比对：忽略标点和空白"""
    punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~“”？，！【】（）、。：；’‘……——"""
    translator = str.maketrans('', '', punctuation)
    text = sanitize_ai_output(text) # 先清洗
    text = re.sub(r'\d+[.、]', '', text)
    text = re.sub(r'\s+', '', text)
    return text.translate(translator)

def smart_split_text(text, chunk_size=800):
    """分块稍微改小一点，保证AI注意力集中在动作分析上"""
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
        
        # 视觉评分逻辑
        if length > 35: status = "❌ 太长 (需再拆)"
        elif length < 6: status = "⚡ 快切/动作"
        else: status = "✅ 标准镜头"
            
        data.append({
            "序号": i+1,
            "分镜内容": clean_content,
            "字数": length,
            "类型": status
        })
    return pd.DataFrame(data)

# --- 主程序 ---
st.title("🎬 导演引擎 V16 (动作回归版)")

uploaded_file = st.file_uploader("📂 上传 TXT", type=['txt'])

if uploaded_file:
    raw = uploaded_file.read().decode("utf-8")
    flat_input = clean_text_for_ai(raw)
    input_pure_len = len(normalize_text_for_comparison(flat_input))
    chunks = smart_split_text(flat_input)
    
    st.info(f"原文已就绪：{input_pure_len} 个有效汉字。正在准备按【动作/场景】进行拆解。")

    st.markdown("---")
    
    if st.button("🚀 开始动作分镜拆解", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            full_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # --- V16 核心 Prompt：回归初心 ---
            system_prompt = """
            你是一个严格的电影分镜师。
            请将用户输入的文案，按照【镜头切换逻辑】进行分行处理。

            【必须遵守的 3 大切分规则】：
            1. **动作改变即切分**：
               - 如果一句话里包含两个连续动作，必须换行。
               - 例如：“他把我推倒在床上，开始画画” -> 必须切分为两行：“他把我推倒在床上”、“开始画画”。
            2. **角色/场景切换即切分**：
               - 对话人改变，或者时间/地点发生流逝，必须换行。
            3. **强制长度限制**：
               - 任何一行不得超过 35 字。如果原文太长，请在标点符号处切开。

            【绝对禁令】：
            - **严禁修改原文**：不要改字，不要删字，不要加字。
            - **严禁添加描述**：不要加括号，不要加画面说明，只保留原文。
            - **不要合并**：不要因为句子短就合并，只要动作变了就必须切！
            """

            try:
                for i, chunk in enumerate(chunks):
                    status_text.markdown(f"**🎬 正在分析第 {i+1}/{len(chunks)} 部分的动作画面...**")
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文本进行分镜切分：\n{chunk}"}
                        ],
                        temperature=0.1 # 低温，严谨
                    )
                    
                    # 获取结果并清洗
                    ai_raw_text = response.choices[0].message.content
                    # 强制清洗：确保没有括号里的废话
                    cleaned_text = sanitize_ai_output(ai_raw_text)
                    
                    full_results.append(cleaned_text)
                    progress_bar.progress((i + 1) / len(chunks))

                # 合成
                combined = "\n".join(full_results)
                final_lines = [line.strip() for line in combined.split('\n') if line.strip()]
                
                # 重建输出
                final_output_text = ""
                raw_output_content = ""
                for idx, line in enumerate(final_lines):
                    clean = re.sub(r'^\d+[.、]\s*', '', line)
                    final_output_text += f"{idx+1}. {clean}\n"
                    raw_output_content += clean

                # --- 结果展示与核对 ---
                st.success("✅ 分镜拆解完成！")
                
                output_pure_len = len(normalize_text_for_comparison(raw_output_content))
                diff = output_pure_len - input_pure_len
                
                # 看板
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("原文汉字数", f"{input_pure_len}")
                m2.metric("分镜汉字数", f"{output_pure_len}")
                
                if diff == 0:
                    m3.metric("内容完整度", "完美无损 ✅", delta="0", delta_color="normal")
                else:
                    m3.metric("偏差值", f"{diff}", delta="异常", delta_color="inverse")
                    
                m4.metric("分镜总组数", f"{len(final_lines)}", help="组数越多，说明动作拆解越细致")

                if abs(diff) > 5:
                    st.error(f"⚠️ 警告：检测到 {abs(diff)} 字的偏差，请检查 AI 是否有遗漏。")

                # 内容区
                c1, c2 = st.columns([1.5, 1])
                
                with c1:
                    st.subheader("📝 动作分镜脚本")
                    st.text_area("结果预览", value=final_output_text, height=650)
                    st.download_button("📥 下载分镜", data=final_output_text, file_name="动作分镜.txt")

                with c2:
                    st.subheader("📊 画面分析表")
                    df = parse_df(final_output_text)
                    st.dataframe(
                        df,
                        column_config={
                            "序号": st.column_config.NumberColumn(width="small"),
                            "分镜内容": st.column_config.TextColumn(width="large"),
                            "字数": st.column_config.ProgressColumn(
                                "画面负荷", 
                                format="%d", 
                                min_value=0, 
                                max_value=40
                            ),
                            "类型": st.column_config.TextColumn(width="medium")
                        },
                        hide_index=True,
                        height=650
                    )

            except Exception as e:
                st.error(f"❌ 错误: {e}")
