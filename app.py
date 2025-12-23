import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 页面基础配置 ---
st.set_page_config(
    page_title="导演引擎 V14 (视觉动词版)",
    page_icon="🎬",
    layout="wide"
)

# --- CSS样式优化 ---
st.markdown("""
<style>
    /* 强化数据看板 */
    .metric-container {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 10px;
        border-radius: 5px;
    }
    .stDataFrame { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V14")
    st.caption("核心：基于视觉动词的逻辑切分")
    
    api_key = st.text_input("API Key", type="password", placeholder="sk-...")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["gpt-4o", "deepseek-chat", "claude-3-5-sonnet-20240620", "gpt-4-turbo"]
    selected_model = st.selectbox("Model ID", model_options, index=0)
    
    if st.checkbox("自定义模型ID"):
        model_id = st.text_input("输入ID", value=selected_model)
    else:
        model_id = selected_model

    st.divider()
    st.markdown("### 🎬 V14 视觉逻辑")
    st.warning("""
    **拒绝机械合并！**
    
    1. **动作切换即切分**：
       - "推门" -> "落下帷幕" (即使字数少也要切)
    2. **对比蒙太奇**：
       - "世人骂我" (切) "男人爱我"
    3. **时空跳跃**：
       - "画画" (切) "日复一日"
    """)

# --- 核心函数 ---

def clean_text_for_ai(text):
    """预处理：去换行"""
    return text.replace("\n", "").replace("\r", "").strip()

def normalize_text_for_comparison(text):
    """仅用于比对汉字数量，忽略标点"""
    punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~“”？，！【】（）、。：；’‘……——"""
    translator = str.maketrans('', '', punctuation)
    text = re.sub(r'\d+[.、]', '', text)
    text = re.sub(r'\s+', '', text)
    return text.translate(translator)

def smart_split_text(text, chunk_size=1000):
    """分块处理，防止长文丢失"""
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
    """生成分析表"""
    lines = full_text.split('\n')
    data = []
    for i, line in enumerate(lines):
        if not line.strip(): continue
        clean_content = re.sub(r'^\d+[.、]\s*', '', line)
        length = len(clean_content)
        
        # 视觉评估逻辑
        if length > 38:
            status = "❌ 画面太满 (需拆分)"
        elif length > 28:
            status = "⚠️ 稍长"
        elif length < 8:
            status = "⚡ 特写/快切"
        else:
            status = "✅ 舒适区 (8-28字)"
            
        data.append({
            "序号": i+1,
            "分镜内容": clean_content,
            "字数": length,
            "视觉状态": status
        })
    return pd.DataFrame(data)

# --- 主程序 ---
st.title("🎬 导演引擎 V14 (视觉动词版)")

uploaded_file = st.file_uploader("📂 上传 TXT", type=['txt'])

if uploaded_file:
    # 1. 初始数据计算
    raw = uploaded_file.read().decode("utf-8")
    flat_input = clean_text_for_ai(raw)
    input_pure_len = len(normalize_text_for_comparison(flat_input))
    
    chunks = smart_split_text(flat_input)
    
    # 显示上传后的基础信息
    st.info(f"文案已就绪。原文共 {len(flat_input)} 字符 (含标点)，已切分为 {len(chunks)} 个处理单元。")

    st.markdown("---")
    
    if st.button("🚀 启动视觉动词分析", type="primary"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            full_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # --- V14 核心 Prompt (彻底重写) ---
            system_prompt = """
            你是一名极其资深的电影分镜导演。你的核心工作不是“排版”，而是“将文字翻译成画面”。
            
            【至高原则：无损 + 视觉动词切分】
            1. **严禁遗漏**：原文的每一个字都必须保留。
            2. **切分逻辑（必须执行）**：
               不要因为句子短就合并！要看画面是否变化！
               
               - **动作变化必切**：
                 ❌ 错误：我把草稿打了出来，正上色，门突然被推开，床帷顺势落下。 (这是4个画面，不能挤在一行！)
                 ✅ 正确：
                 我把草稿打了出来，正上色
                 门突然被推开
                 床帷顺势落下
                 
               - **强对比必切**：
                 ❌ 错误：世间女子骂我伤风败俗，可男人们却视若珍宝。
                 ✅ 正确：
                 世间女子骂我伤风败俗
                 可男人们却视若珍宝 (镜头反打)
                 
               - **时空变化必切**：
                 ❌ 错误：将春宫十八式用在我身上，日复一日。
                 ✅ 正确：
                 将春宫十八式——用在我身上
                 日复一日 (时间流逝镜头)

            3. **长度风控**：
               - 理想分镜长度：10-30字。
               - 绝对上限：38字（如果画面没变但字太长，在标点处切开）。
            """

            try:
                for i, chunk in enumerate(chunks):
                    status_text.markdown(f"**🎬 正在导演第 {i+1}/{len(chunks)} 场戏...**")
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对这段文本进行视觉分镜拆解：\n{chunk}"}
                        ],
                        temperature=0.1 # 保持低温，确保准确
                    )
                    
                    full_results.append(response.choices[0].message.content)
                    progress_bar.progress((i + 1) / len(chunks))

                # 合成与清洗
                combined = "\n".join(full_results)
                final_lines = [line.strip() for line in combined.split('\n') if line.strip()]
                
                # 重建序号与内容
                final_output_text = ""
                raw_output_content = ""
                for idx, line in enumerate(final_lines):
                    clean = re.sub(r'^\d+[.、]\s*', '', line)
                    # 再次清洗可能残留的markdown符号
                    clean = clean.replace("**", "")
                    final_output_text += f"{idx+1}. {clean}\n"
                    raw_output_content += clean

                # --- 结果看板 (修复版) ---
                st.success("✅ 分镜处理完成！")
                
                # 计算输出数据
                output_pure_len = len(normalize_text_for_comparison(raw_output_content))
                diff = output_pure_len - input_pure_len
                
                # 使用 Columns 布局进行对比展示
                st.markdown("### 📊 无损核验数据看板")
                
                m1, m2, m3, m4 = st.columns(4)
                
                # 1. 原文数据 (无标点)
                m1.metric(
                    label="📄 原文纯净字数", 
                    value=f"{input_pure_len}",
                    help="去除标点后的纯汉字数量"
                )
                
                # 2. 分镜数据 (无标点)
                m2.metric(
                    label="🎬 分镜纯净字数", 
                    value=f"{output_pure_len}",
                    help="AI输出结果的纯汉字数量"
                )
                
                # 3. 偏差值 (最重要)
                m3.metric(
                    label="⚖️ 内容偏差", 
                    value=f"{diff}",
                    delta_color="off" if diff == 0 else "inverse",
                    help="0 表示完美无损。正数=重复，负数=漏字"
                )
                
                # 4. 平均节奏
                avg_len = round(len(raw_output_content)/len(final_lines), 1)
                m4.metric(
                    label="平均每镜字数", 
                    value=f"{avg_len}",
                    delta="偏快" if avg_len < 15 else ("偏慢" if avg_len > 30 else "完美"),
                    delta_color="normal" if 15 <= avg_len <= 30 else "inverse"
                )

                if abs(diff) > 5:
                    st.error(f"⚠️ 警告：检测到 {abs(diff)} 个字的差异，请务必检查下方内容！")

                # 内容展示区
                c1, c2 = st.columns([1.5, 1])
                
                with c1:
                    st.subheader("📝 视觉分镜脚本")
                    st.text_area("内容预览", value=final_output_text, height=650)
                    st.download_button("📥 下载分镜脚本", data=final_output_text, file_name="视觉分镜V14.txt")

                with c2:
                    st.subheader("⏱️ 视觉节奏表")
                    df = parse_df(final_output_text)
                    st.dataframe(
                        df,
                        column_config={
                            "序号": st.column_config.NumberColumn(width="small"),
                            "分镜内容": st.column_config.TextColumn(width="large"),
                            "字数": st.column_config.ProgressColumn(
                                "画面时长", 
                                format="%d", 
                                min_value=0, 
                                max_value=40
                            ),
                            "视觉状态": st.column_config.TextColumn(width="medium")
                        },
                        hide_index=True,
                        height=650
                    )

            except Exception as e:
                st.error(f"❌ 运行出错: {e}")
