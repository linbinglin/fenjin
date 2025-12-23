import streamlit as st
from openai import OpenAI
import re
import pandas as pd
import string

# --- 页面基础配置 ---
st.set_page_config(
    page_title="导演引擎 V12 (无损旗舰版)",
    page_icon="🎬",
    layout="wide"
)

# --- 自定义 CSS (导演级黑深色模式适配) ---
st.markdown("""
<style>
    .metric-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #ff4b4b;
        margin-bottom: 20px;
    }
    .stProgress > div > div > div > div {
        background-color: #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 导演引擎 V12")
    st.caption("旗舰版：智能纠错 + 视觉重音切分")
    
    api_key = st.text_input("API Key", type="password", placeholder="sk-...")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    
    model_options = ["gpt-4o", "deepseek-chat", "claude-3-5-sonnet-20240620", "gpt-4-turbo", "gpt-3.5-turbo"]
    selected_model = st.selectbox("Model ID", model_options, index=0)
    
    if st.checkbox("自定义模型ID"):
        model_id = st.text_input("输入ID", value=selected_model)
    else:
        model_id = selected_model

    st.divider()
    st.markdown("### 🎬 V12 视觉切分逻辑")
    st.info("""
    1. **情绪重音**：如“日复一日”、“恨不得”等情绪词单独成镜。
    2. **动作拆解**：一个动作（推倒）+ 一个反应（看着）= 两个分镜。
    3. **零损耗**：忽略标点差异，严查文字丢失。
    """)

# --- 核心逻辑函数 ---

def clean_text_for_ai(text):
    """预处理：去格式，变纯文本"""
    return text.replace("\n", "").replace("\r", "").strip()

def normalize_text_for_comparison(text):
    """
    清洗文本以便进行【内容级】比对。
    去除所有标点符号、空格、换行、数字序号。
    只保留纯汉字/英文单词。
    """
    # 去除常见的中文标点和英文标点
    punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~“”？，！【】（）、。：；’‘……"""
    translator = str.maketrans('', '', punctuation)
    
    # 1. 去除序号 (1. 或 100.)
    text = re.sub(r'\d+[.、]', '', text)
    # 2. 去除换行和空格
    text = re.sub(r'\s+', '', text)
    # 3. 去除标点
    text = text.translate(translator)
    return text

def smart_split_text(text, chunk_size=1000):
    """
    更智能的分块：按句号切分，每块约1000字。
    """
    sentences = re.split(r'([。！？])', text)
    chunks = []
    current = ""
    
    # 重新拼接
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
    """生成右侧分析表格数据"""
    lines = full_text.split('\n')
    data = []
    for i, line in enumerate(lines):
        if not line.strip(): continue
        # 清洗序号，获取纯内容
        clean_content = re.sub(r'^\d+[.、]\s*', '', line)
        length = len(clean_content)
        # 状态判断
        if length > 35: status = "⚠️ 拥挤"
        elif length < 5: status = "⚡ 快切"
        else: status = "✅ 完美"
        
        data.append({
            "序号": i+1,
            "分镜内容": clean_content,
            "字数": length,
            "视觉节奏": status
        })
    return pd.DataFrame(data)

# --- 主程序 ---
st.title("🎬 导演引擎 V12 (无损还原版)")

# 1. 上传
uploaded_file = st.file_uploader("📂 第一步：上传剧本 TXT", type=['txt'])

if uploaded_file:
    raw = uploaded_file.read().decode("utf-8")
    flat_input = clean_text_for_ai(raw)
    input_len_display = len(flat_input)
    
    # 纯净版长度（用于比对，不含标点）
    input_pure_len = len(normalize_text_for_comparison(flat_input))
    
    chunks = smart_split_text(flat_input)
    total_chunks = len(chunks)

    # 状态栏
    col1, col2, col3 = st.columns(3)
    col1.metric("原文总字数", f"{input_len_display}")
    col2.metric("剧情切片数", f"{total_chunks} 块")
    
    # 2. 生成
    st.markdown("---")
    if st.button("🚀 启动 V12 导演引擎", type="primary"):
        if not api_key:
            st.error("请先配置 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            full_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Prompt 强化：加入了你喜欢的“情绪切分”示例
                system_prompt = """
                你是一个电影分镜导演。请将文本拆解为分镜脚本。
                
                【核心指令】：
                1. **必须无损**：严禁删减原文任何文字。
                2. **格式**：一行一个分镜，不要加序号（系统会加）。
                3. **切分逻辑（模仿以下风格）**：
                   - "笑着说画技再好哪比得上亲身体会" -> 拆分为：
                     笑着说画技再好
                     哪比得上亲身体会
                   - "用在我身上日复一日" -> 拆分为：
                     ——用在我身上
                     日复一日
                4. **硬性限制**：单行绝对不可超过35字，长句必须在语义停顿处切开。
                """

                for i, chunk in enumerate(chunks):
                    status_text.markdown(f"**🎬 正在处理第 {i+1}/{total_chunks} 幕...**")
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"处理这段剧情：\n{chunk}"}
                        ],
                        temperature=0.1 # 极低温度保证不乱改字
                    )
                    
                    res_text = response.choices[0].message.content
                    full_results.append(res_text)
                    progress_bar.progress((i + 1) / total_chunks)

                # 合成
                combined = "\n".join(full_results)
                # 清洗空行
                final_lines = [line.strip() for line in combined.split('\n') if line.strip()]
                
                # 重建序号文本
                final_output_text = ""
                raw_output_content = ""
                for idx, line in enumerate(final_lines):
                    clean = re.sub(r'^\d+[.、]\s*', '', line)
                    final_output_text += f"{idx+1}. {clean}\n"
                    raw_output_content += clean

                # --- 结果分析区 ---
                st.success("🎉 分镜生成完毕！")
                
                # 关键：计算纯汉字偏差（忽略标点）
                output_pure_len = len(normalize_text_for_comparison(raw_output_content))
                diff = output_pure_len - input_pure_len
                
                # 统计面板
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("生成分镜组数", f"{len(final_lines)} 组")
                m2.metric("原文纯净字数(无标点)", f"{input_pure_len}")
                m3.metric("分镜纯净字数(无标点)", f"{output_pure_len}")
                
                # 智能偏差显示
                if diff == 0:
                    m4.metric("内容完整度", "完美无损 ✅", delta="0", delta_color="normal")
                else:
                    m4.metric("内容偏差", f"{diff} 字", delta="可能漏字" if diff < 0 else "可能重复", delta_color="inverse")
                    if abs(diff) > 10:
                        st.error(f"⚠️ 警告：检测到 {abs(diff)} 个汉字的实质性差异，请检查右侧表格。")

                # 双栏展示
                c_left, c_right = st.columns([1.5, 1])
                
                with c_left:
                    st.subheader("📝 分镜脚本编辑器")
                    st.text_area("可直接复制", value=final_output_text, height=600)
                    st.download_button("📥 下载脚本", data=final_output_text, file_name="无损分镜.txt")

                with c_right:
                    st.subheader("📊 视觉节奏表")
                    df = parse_df(final_output_text)
                    st.dataframe(
                        df,
                        column_config={
                            "序号": st.column_config.NumberColumn(width="small"),
                            "字数": st.column_config.ProgressColumn(
                                "时长估算", 
                                format="%d 字", 
                                min_value=0, 
                                max_value=40
                            ),
                            "视觉节奏": st.column_config.TextColumn(width="small")
                        },
                        hide_index=True,
                        height=600
                    )

            except Exception as e:
                st.error(f"❌ 运行中断：{e}")
