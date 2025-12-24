import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 页面配置 ---
st.set_page_config(
    page_title="全能文案·电影感分镜系统 (V2.0)",
    page_icon="🎬",
    layout="wide"
)

# --- CSS样式优化 (模仿专业软件风格) ---
st.markdown("""
<style>
    .reportview-container {
        background: #f0f2f6;
    }
    .main-header {
        font-size: 2.5rem;
        color: #333;
        font-weight: 700;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
    }
    .metric-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        text-align: center;
    }
    .stDataFrame {
        border: 1px solid #ddd;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 辅助函数 ---
def count_valid_chars(text):
    """统计有效字数（排除标点）"""
    if not text: return 0
    clean_text = re.sub(r'[^\w\u4e00-\u9fa50-9]', '', text)
    return len(clean_text)

def analyze_rhythm(text):
    """分析分镜节奏状态"""
    length = count_valid_chars(text)
    if length == 0: return "❌ 空白", length
    if length < 10: return "🟡 偏短 (快切)", length
    if 10 <= length <= 35: return "✅ 理想 (5秒)", length
    return "🔴 偏长 (需拆分)", length

# --- 侧边栏：核心配置 ---
with st.sidebar:
    st.markdown("## ⚙️ 导演引擎 V2.0")
    
    base_url = st.text_input(
        "接口地址 (Base URL)", 
        value="https://blog.tuiwen.xyz/v1",
        help="例如: https://blog.tuiwen.xyz/v1"
    )

    api_key = st.text_input(
        "API Key (密钥)", 
        type="password",
        value=""
    )

    model_id = st.text_input(
        "Model ID (模型名称)", 
        value="gpt-4o",
        help="推荐使用 gpt-4o 或 claude-3-5-sonnet 以获得最佳逻辑理解能力"
    )
    
    st.info("""
    **V2.0 更新日志：**
    1. 修复了分镜过碎的问题。
    2. 增加了视觉节奏分析面板。
    3. 优化了长难句的语义完整性。
    """)

# --- 主界面 ---
st.markdown('<div class="main-header">🎬 全能文案·电影感分镜系统 (V2.0)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">针对“画面碎片化”深度优化，智能识别主语、动作与场景。</div>', unsafe_allow_html=True)
st.divider()

# 1. 文件上传
uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=["txt"])

if uploaded_file is not None:
    raw_text = uploaded_file.read().decode("utf-8")
    
    # 预处理：去重、去空行、压缩为一行 (防AI偷懒的核心步骤)
    flattened_text = raw_text.replace('\n', '').replace('\r', '').strip()
    input_count = count_valid_chars(flattened_text)

    # 显示原文状态
    st.success(f"📄 原文已装载 | 总字数: {input_count} 字 | 已进行“反懒惰”压缩处理")
    
    # 生成按钮
    if st.button("🚀 启动视觉分镜引擎", type="primary"):
        if not api_key:
            st.error("请先配置 API Key")
            st.stop()
            
        # --- 核心 Prompt (经过针对性优化的“导演模式”) ---
        system_prompt = f"""
你是由好莱坞资深剪辑师训练的AI分镜导演。你的任务是将一段被压缩成一行的文本，还原为适合短视频制作的“视觉分镜脚本”。

【原文本】
{flattened_text}

【绝对禁止】
1. 禁止输出原文本没有的内容。
2. 禁止出现“碎片化”分镜（如单独的“毫无用处”、“早已买好了船票”这种无头无尾的短语，必须和主语或上一句动作合并）。
3. 禁止改变故事原意。

【分镜拆解逻辑 - 请严格遵守】
1. **语义完整性优先**：不要机械地按字数切分。每一行分镜必须是一个完整的“视觉画面”或“完整的台词意群”。
   - 错误示范：
     1. 皇上翻遍后宫只为
     2. 找出酒后爬龙床的
     3. 官女
   - 正确示范：
     1. 皇上翻遍后宫只为找出酒后爬龙床的官女
2. **动作与场景切换**：
   - 遇到由“我”转“他”时，必须换行。
   - 遇到新场景（如从卧室转到大厅）时，必须换行。
   - 遇到明显的动作变化（如从“坐着”变“站起摔杯子”）时，必须换行。
3. **时长控制（黄金法则）**：
   - 理想长度：每行 15-35 个字（约 3-5 秒）。
   - 如果一句话太长（超过 40 字），请在逗号或逻辑转折处切分，但切分后的半句必须有意义。
   - 如果一句话太短（少于 8 字），请判断它是否能合并到上一句动作中？如果不能合并（如强调句），则保留。

【输出格式】
纯文本列表，每行一个数字开头，不要Markdown加粗。
1.第一段分镜内容
2.第二段分镜内容
...
"""

        client = OpenAI(api_key=api_key, base_url=base_url)
        
        st.subheader("📊 正在进行视觉单元规划...")
        result_container = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": "你是一个严谨的电影分镜师。你极度厌恶破碎的句子。你擅长将文本划分为完整的视觉动作单元。"},
                    {"role": "user", "content": system_prompt}
                ],
                stream=True,
                temperature=0.6, # 降低温度，增加逻辑稳定性
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    result_container.text_area("生成预览 (实时)", value=full_response, height=400)
            
            # --- 后处理与数据分析 (复刻图四的功能) ---
            st.divider()
            st.subheader("📈 视觉逻辑稽核面板")
            
            # 1. 解析生成的内容
            lines = []
            raw_lines = full_response.strip().split('\n')
            
            output_valid_chars = 0
            
            for line in raw_lines:
                # 提取内容（去除 1. 这种序号）
                clean_line = re.sub(r'^\d+\.?\s*', '', line).strip()
                if clean_line:
                    status, length = analyze_rhythm(clean_line)
                    output_valid_chars += length
                    lines.append({
                        "分镜序号": len(lines) + 1,
                        "分镜内容": clean_line,
                        "字数": length,
                        "节奏状态": status
                    })
            
            # 2. 统计数据展示
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("原文总字数", input_count)
            col2.metric("生成分镜组数", len(lines))
            col3.metric("处理后总字数", output_valid_chars)
            
            diff = output_valid_chars - input_count
            col4.metric("偏差值 (漏字监控)", f"{diff} 字", delta_color="inverse")
            
            if abs(diff) > 10:
                st.error(f"⚠️ 警报：AI 可能遗漏或添加了部分内容（偏差 {diff} 字），请检查下方详情。")
            else:
                st.success("✅ 完美还原：内容无损，逻辑完整。")

            # 3. 详细数据表 (类似图四的右侧栏)
            df = pd.DataFrame(lines)
            st.markdown("### 🎬 实时视觉节奏分析")
            
            # 使用 dataframe 高亮显示
            def highlight_status(val):
                color = 'black'
                if '❌' in val: color = 'red'
                elif '🟡' in val: color = '#D4AF37' # Gold
                elif '🔴' in val: color = 'orange'
                elif '✅' in val: color = 'green'
                return f'color: {color}; font-weight: bold;'

            st.dataframe(
                df.style.map(highlight_status, subset=['节奏状态']),
                use_container_width=True,
                height=500,
                column_config={
                    "分镜序号": st.column_config.NumberColumn("序号", width="small"),
                    "分镜内容": st.column_config.TextColumn("分镜文案 (Visual Script)", width="large"),
                    "字数": st.column_config.ProgressColumn("时长预估", min_value=0, max_value=50, format="%d 字"),
                    "节奏状态": st.column_config.TextColumn("AI 建议", width="medium"),
                }
            )

        except Exception as e:
            st.error(f"发生错误: {str(e)}")
