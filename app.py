import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 页面基础配置 ---
st.set_page_config(
    page_title="导演引擎 V13 (视觉聚合版)",
    page_icon="🎬",
    layout="wide"
)

# --- 自定义 CSS ---
st.markdown("""
<style>
    .metric-box { background-color: #f0f2f6; padding: 15px; border-radius: 8px; }
    /* 优化表格显示 */
    .stDataFrame { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V13")
    st.caption("版本特性：拒绝破碎，智能聚合")
    
    api_key = st.text_input("API Key", type="password", placeholder="sk-...")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["gpt-4o", "deepseek-chat", "claude-3-5-sonnet-20240620", "gpt-4-turbo", "gpt-3.5-turbo"]
    selected_model = st.selectbox("Model ID", model_options, index=0)
    
    if st.checkbox("自定义模型ID"):
        model_id = st.text_input("输入ID", value=selected_model)
    else:
        model_id = selected_model

    st.divider()
    st.markdown("### 🎬 V13 聚合逻辑")
    st.info("""
    1. **优先合并**：只要不超35字，尽量不换行。
    2. **拒绝碎词**：严禁出现 "用在我身上" 这种5字短句单独成行（除非是极特殊的强调）。
    3. **黄金时长**：目标是让每行落在 20-35 字区间。
    """)

# --- 核心逻辑 ---

def clean_text_for_ai(text):
    return text.replace("\n", "").replace("\r", "").strip()

def normalize_text_for_comparison(text):
    """用于无损比对：去标点、去空格、去序号"""
    punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~“”？，！【】（）、。：；’‘……——"""
    translator = str.maketrans('', '', punctuation)
    text = re.sub(r'\d+[.、]', '', text)
    text = re.sub(r'\s+', '', text)
    text = text.translate(translator)
    return text

def smart_split_text(text, chunk_size=1200):
    """
    稍微增大分块大小，让AI有更多的上下文来判断合并
    """
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
        
        # V13 评分标准调整
        if length > 35: 
            status = "⚠️ 太长 (超35)"
        elif length < 10: 
            status = "⚠️ 太碎 (少于10)" # 新增太短警告
        elif 20 <= length <= 35:
            status = "✅ 黄金流 (20-35)"
        else:
            status = "🆗 正常 (10-20)"
        
        data.append({
            "序号": i+1,
            "分镜内容": clean_content,
            "字数": length,
            "视觉状态": status
        })
    return pd.DataFrame(data)

# --- 主程序 ---
st.title("🎬 导演引擎 V13 (智能聚合版)")
st.markdown("针对“分镜太碎”问题深度优化。核心策略：**能合则合，非长不切**。")

uploaded_file = st.file_uploader("📂 上传 TXT", type=['txt'])

if uploaded_file:
    raw = uploaded_file.read().decode("utf-8")
    flat_input = clean_text_for_ai(raw)
    input_pure_len = len(normalize_text_for_comparison(flat_input))
    
    chunks = smart_split_text(flat_input)
    total_chunks = len(chunks)

    col1, col2 = st.columns(2)
    col1.metric("原文总字数", f"{len(flat_input)}")
    col2.metric("切片数", f"{total_chunks}")
    
    st.markdown("---")
    if st.button("🚀 启动 V13 聚合引擎", type="primary"):
        if not api_key:
            st.error("请先配置 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            full_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # --- V13 核心 Prompt 修改 ---
                # 移除了所有鼓励切分的指令，增加了“合并”指令
                system_prompt = """
                你是一个专业的电影剪辑师。请将文案处理为分镜脚本。
                
                【最高指令：拒绝破碎感】
                1. **聚合原则**：只要一句话（包含逗号的短句）加起来不超过35个字，且属于同一场景，**必须合并在同一行**。
                2. **禁止碎词**：严禁将一个完整的谓语或宾语切断。
                   - ❌ 错误： "将那些画上的" (换行) "用在我身上"
                   - ✅ 正确： "将那些画上的春宫十八式——用在我身上" (合并)
                3. **硬性限制**：
                   - 单行上限：35字（超过则必须在标点处切开）。
                   - 理想长度：20-35字（这能保证约5秒的画面停留）。
                4. **必须无损**：严禁删字，严禁加字。
                """

                for i, chunk in enumerate(chunks):
                    status_text.markdown(f"**🔄 正在聚合处理第 {i+1}/{total_chunks} 区块...**")
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文案进行分镜规划（注意合并短句）：\n{chunk}"}
                        ],
                        temperature=0.1
                    )
                    
                    res_text = response.choices[0].message.content
                    full_results.append(res_text)
                    progress_bar.progress((i + 1) / total_chunks)

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

                # --- 结果分析 ---
                st.success("✨ 处理完成！破碎感已修复。")
                
                output_pure_len = len(normalize_text_for_comparison(raw_output_content))
                diff = output_pure_len - input_pure_len
                
                # 统计
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("生成分镜组数", f"{len(final_lines)} 组", 
                          help="组数越少，说明聚合效果越好")
                m2.metric("平均每镜字数", f"{round(len(raw_output_content)/len(final_lines), 1)} 字",
                          help="理想值应在 15-25 之间")
                m3.metric("无损核验", f"{output_pure_len}", 
                          delta=f"{diff}", delta_color="inverse")
                
                if abs(diff) > 10:
                    st.warning("⚠️ 注意：字数存在差异，请检查是否因合并导致漏字。")

                # 内容展示
                c_left, c_right = st.columns([1.5, 1])
                
                with c_left:
                    st.subheader("📝 聚合分镜脚本")
                    st.text_area("内容", value=final_output_text, height=600)
                    st.download_button("📥 下载脚本", data=final_output_text, file_name="聚合分镜.txt")

                with c_right:
                    st.subheader("📊 视觉节奏表 (V13)")
                    df = parse_df(final_output_text)
                    st.dataframe(
                        df,
                        column_config={
                            "序号": st.column_config.NumberColumn(width="small"),
                            "分镜内容": st.column_config.TextColumn(width="large"),
                            "字数": st.column_config.ProgressColumn(
                                "节奏条", 
                                format="%d", 
                                min_value=0, 
                                max_value=40
                            ),
                            "视觉状态": st.column_config.TextColumn(width="medium")
                        },
                        hide_index=True,
                        height=600
                    )

            except Exception as e:
                st.error(f"❌ 错误：{e}")
