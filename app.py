import streamlit as st
from openai import OpenAI
import re

# 设置页面配置
st.set_page_config(
    page_title="AI 电影解说分镜助手",
    page_icon="🎬",
    layout="wide"
)

# --- 辅助函数：计算字数（不含标点） ---
def count_valid_chars(text):
    """
    统计文本中的有效字符数（汉字、字母、数字），排除标点符号和空格。
    """
    if not text:
        return 0
    # 使用正则替换掉所有标点符号和空白字符
    # \w 匹配字母数字下划线，\u4e00-\u9fa5 匹配汉字
    # 反向逻辑：将不是汉字、字母、数字的内容替换为空
    clean_text = re.sub(r'[^\w\u4e00-\u9fa50-9]', '', text)
    return len(clean_text)

# --- 侧边栏：配置设置 ---
st.sidebar.header("⚙️ 参数配置")

# 1. API 配置
base_url = st.sidebar.text_input(
    "API Base URL (中转接口地址)", 
    value="https://blog.tuiwen.xyz/v1",
    help="请填写Base URL，通常以 /v1 结尾。注意：代码会自动追加 /chat/completions"
)

api_key = st.sidebar.text_input(
    "API Key (密钥)", 
    type="password",
    help="请输入您的 API Key"
)

# 2. 模型选择 (重点需求 2 & 3)
model_id = st.sidebar.text_input(
    "Model ID (模型名称)", 
    value="gpt-4o",
    placeholder="例如: gpt-4o, deepseek-chat, claude-3-5-sonnet",
    help="请输入您想使用的模型名称，支持 DeepSeek, GPT-4o, Claude 等"
)

# --- 主界面 ---
st.title("🎬 AI 电影解说分镜生成器")
st.markdown("### 逐字逐句分析，精准卡点 5 秒分镜")

# 1. 文件上传 (代码要求 1)
uploaded_file = st.file_uploader("📂 选择本地 TXT 文档", type=["txt"])

if uploaded_file is not None:
    # 读取文件
    raw_text = uploaded_file.read().decode("utf-8")
    
    # --- 预处理：删除原段落 (重点需求 7) ---
    # 将文本压缩成一行，防止 AI 偷懒直接用原文段落
    flattened_text = raw_text.replace('\n', '').replace('\r', '').strip()
    
    # 统计原文有效字数
    input_count = count_valid_chars(flattened_text)

    # --- 显示原文信息面板 (新增功能) ---
    st.info(f"📄 原文已加载 | 有效字数 (不含标点): **{input_count}** 字")
    
    with st.expander("点击查看处理前的“被压缩”原文 (用于防AI偷懒)"):
        st.write(flattened_text)

    # 生成按钮
    if st.button("🚀 开始生成分镜", type="primary"):
        if not api_key:
            st.error("❌ 请在左侧侧边栏输入 API Key")
            st.stop()
        
        if not flattened_text:
            st.error("❌ 文本内容为空")
            st.stop()

        # --- 构建 Prompt (核心逻辑) ---
        # 严格按照你的 1-8 点需求编写 Prompt
        system_prompt = f"""
你是一个优秀的电影解说分镜员。请根据用户提供的文本生成分镜脚本。

【重要原则】
1. **完整性**：整理后的内容不可遗漏原文中的任何一句话，一个字。不能改变原文故事结构，禁止添加原文以外任何内容。
2. **时长控制**：必须考虑到配音时长。一个分镜只能停留五秒钟，约35个字符。如果原文句子过长，必须强行拆分成下一行分镜。
3. **分段逻辑**：
   - 角色对话切换 -> 下一个分镜
   - 场景切换 -> 下一个分镜
   - 动作画面改变 -> 下一个分镜
   - 单句超过35字 -> 下一个分镜

【输出格式】
请直接输出分镜列表，格式如下（纯数字加点）：
1.第一段文案
2.第二段文案
...

【待处理文本】
{flattened_text}

请注意：用户上传的文本已经去除了段落，你需要根据语义重新理解并按照上述逻辑进行“微创”分段。
"""

        # 初始化客户端
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        st.divider()
        st.subheader("🎥 分镜生成结果")
        
        result_container = st.empty()
        full_response = ""

        try:
            # 流式输出 (Streamlit Cloud 体验更好)
            stream = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": "你是一个严格的电影分镜与时序控制专家。"},
                    {"role": "user", "content": system_prompt}
                ],
                stream=True,
                temperature=0.7 # 稍微降低创造性，保证忠实原文
            )

            # 接收流
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    result_container.markdown(full_response)
            
            # --- 后处理：结果字数统计 (新增功能) ---
            # 去掉序号 (1. 2. 等) 再统计，以免影响字数对比
            # 正则：去除行首的数字和点
            content_for_count = re.sub(r'^\d+\.', '', full_response, flags=re.MULTILINE)
            output_count = count_valid_chars(content_for_count)
            
            # --- 结果对比面板 ---
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("原文有效字数", input_count)
            col2.metric("分镜有效字数", output_count)
            
            diff = output_count - input_count
            if diff == 0:
                col3.success("✅ 字数完美匹配")
            elif abs(diff) < 5:
                col3.warning(f"⚠️ 差异微小 ({diff}字)")
            else:
                col3.error(f"❌ 字数差异较大 ({diff}字)，请检查AI是否遗漏")

        except Exception as e:
            st.error(f"发生错误: {str(e)}")
            st.markdown("建议检查：\n1. API Key 是否正确\n2. 模型名称是否存在\n3. 余额是否充足")
