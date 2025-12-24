import streamlit as st
from openai import OpenAI
import re

# ====================
# 1. 页面配置与样式
# ====================
st.set_page_config(
    page_title="全能文案·电影感分镜系统 (V11)",
    page_icon="🎬",
    layout="wide"
)

# 自定义CSS以接近截图风格
st.markdown("""
<style>
    .main-header {font-size: 2rem; font-weight: bold; margin-bottom: 1rem;}
    .sub-header {font-size: 1.2rem; font-weight: bold; margin-top: 2rem; color: #444;}
    .stat-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stat-value {font-size: 2rem; font-weight: bold; color: #31333F;}
    .stat-label {font-size: 1rem; color: #666;}
    .stTextArea textarea {font-size: 16px; line-height: 1.6;}
    .success-text {color: green; font-weight: bold;}
    .error-text {color: red; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ====================
# 2. 侧边栏配置 (API设置)
# ====================
with st.sidebar:
    st.markdown("### ⚙️ 导演引擎 V11 设置")
    
    api_key = st.text_input("API Key", type="password", help="请输入你的API Key")
    base_url = st.text_input("接口地址 (Base URL)", value="https://blog.tuiwen.xyz/v1", help="第三方中转接口地址")
    
    # 模型选择 (预设 + 自定义)
    model_options = ["deepseek-chat", "gpt-4o", "claude-3-5-sonnet", "gemini-pro", "grok-beta", "自定义"]
    selected_model = st.selectbox("Model ID (模型选择)", model_options)
    
    if selected_model == "自定义":
        model_id = st.text_input("请输入自定义模型名称")
    else:
        model_id = selected_model

    st.info("💡 提示：请确保你的账户余额充足。")

# ====================
# 3. 工具函数
# ====================

def clean_text_for_count(text):
    """
    去除所有标点符号和空格，只保留汉字、字母、数字。
    用于精准比对字数，防止标点差异导致的误判。
    """
    if not text:
        return ""
    # 正则：排除所有非单词字符（但保留中文）
    # \u4e00-\u9fa5 是中文字符范围
    pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9]')
    return re.sub(pattern, '', text)

def process_storyboard(client, model, text):
    """
    调用LLM进行分镜处理
    """
    # 核心指令：严格按照用户要求的8点逻辑编写
    system_prompt = f"""
你是一个优秀的电影解说分镜员。请严格按照以下规则对用户提供的文本进行分镜处理：

1. **逐字逐句理解**：理解文本内容，不能遗漏任何信息。
2. **分镜触发条件**：
   - 角色对话切换时。
   - 场景切换时。
   - 动作画面发生改变时。
   - 上述情况发生时，必须设定为下一个分镜。
3. **绝对完整性**：整理后的内容**不可遗漏原文中的任何一句话、一个字**，不能改变原文故事结构，**禁止添加**原文以外的任何内容（如“镜头描述”、“画面指令”等，只保留原文文案）。
4. **格式要求**：每组分镜前标上数字序号（1. 2. 3. ...），每组分镜独占一行。
5. **分镜逻辑**：当故事从一个场景切换到另一个场景时，请务必另起新的分镜。
6. **时长限制**：每个分镜文案严格控制在 **35个字符以内**（对应约5秒视频时长）。如果原句过长，必须在符合语义逻辑的地方进行切分，确保不超过35字。
7. **数据源处理**：请忽略原文的段落格式，将其视为连续的文本流重新进行分镜规划。

输出示例：
1.8岁那年家里穷得揭不开锅了
2.怀孕的母亲带着我在寺外乞讨
3.我把僧人端来的粥饭全给了母亲
4.施粥的将军府老妇人，让人领我过来问
5.都饿成人干了怎么不吃

现在，请对以下文本进行分镜处理：
"""
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            stream=False,
            temperature=0.7 
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

# ====================
# 4. 主界面逻辑
# ====================

st.markdown('<div class="main-header">🎬 全能文案·电影感分镜系统 (V11)</div>', unsafe_allow_html=True)
st.markdown('针对“音画不同步”、“内容重叠”深度优化。适配全题材文案。')

# 文件上传区域
uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    # 读取文件
    raw_content = uploaded_file.read().decode("utf-8")
    
    # 预处理：删除原文的所有换行符，强制变成一行，防止AI偷懒
    processed_input_text = raw_content.replace("\n", "").replace("\r", "")
    
    # 计算原文纯净字数
    original_clean_count = len(clean_text_for_count(processed_input_text))
    
    st.markdown("### 📄 原文预览 (已自动去除段落格式)")
    with st.expander("点击查看待处理文本", expanded=False):
        st.write(processed_input_text)

    # 提交按钮
    if st.button("🚀 启动视觉无损分镜", type="primary"):
        if not api_key:
            st.error("❌ 请先在左侧侧边栏设置 API Key")
        else:
            with st.spinner('正在分析剧情、拆解分镜、计算时长逻辑... (AI正在思考)'):
                # 初始化客户端
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    
                    # 调用AI
                    result_text = process_storyboard(client, model_id, processed_input_text)
                    
                    # 如果返回的是错误信息
                    if result_text.startswith("Error"):
                        st.error(result_text)
                    else:
                        st.session_state['result'] = result_text
                        st.session_state['original_count'] = original_clean_count
                        st.session_state['raw_input'] = raw_content # 保存原始输入以供对比
                        
                except Exception as e:
                    st.error(f"连接失败: {e}")

# ====================
# 5. 结果展示与视觉逻辑稽核面板
# ====================

if 'result' in st.session_state:
    result = st.session_state['result']
    original_count = st.session_state['original_count']
    
    # 提取分镜后的纯文本（去掉序号和换行，只留内容）用于字数比对
    # 假设AI返回的是 "1. xxx\n2. xxx"，我们需要把数字和点去掉再统计
    # 正则去除行首的数字和点
    clean_result_content = re.sub(r'^\d+\.', '', result, flags=re.MULTILINE)
    output_clean_count = len(clean_text_for_count(clean_result_content))
    
    # 计算偏差
    deviation = output_clean_count - original_count
    
    # 计算分镜组数 (通过换行符粗略估计)
    groups = len(result.strip().split('\n'))

    st.markdown("---")
    st.markdown('<div class="sub-header">📊 视觉逻辑稽核面板</div>', unsafe_allow_html=True)
    
    # 统计数据列
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">原文纯字数</div>
            <div class="stat-value">{original_count}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">生成分镜总数</div>
            <div class="stat-value">{groups} 组</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">处理后纯字数</div>
            <div class="stat-value">{output_clean_count}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        color = "green" if deviation == 0 else "red"
        symbol = "+" if deviation > 0 else ""
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-label">偏差值 (标点除外)</div>
            <div class="stat-value" style="color: {color};">{symbol}{deviation} 字</div>
        </div>
        """, unsafe_allow_html=True)

    # 稽核结果提示
    if deviation == 0:
        st.success("✅ 100% 镜像还原成功：AI未遗漏任何原文内容。")
    elif deviation < 0:
        st.warning(f"⚠️ 警告：AI可能遗漏了 {abs(deviation)} 个字，请检查末尾或过长段落。")
    else:
        st.warning(f"⚠️ 警告：AI可能添加了 {deviation} 个字（或是重复了部分内容）。")

    # 分镜结果编辑器
    st.markdown('<div class="sub-header">🎬 视觉分镜编辑器 (无损还原)</div>', unsafe_allow_html=True)
    st.text_area("生成结果 (可直接复制):", value=result, height=600)

    # 下载按钮
    st.download_button(
        label="📥 下载分镜脚本 (.txt)",
        data=result,
        file_name="storyboard_output.txt",
        mime="text/plain"
    )
