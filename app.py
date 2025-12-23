import streamlit as st
from openai import OpenAI
import re

# --- 工具函数：计算纯文本字数（排除编号、换行、空格） ---
def count_pure_text(text):
    # 去掉编号（例如 1. 或 123.）
    text = re.sub(r'\d+\.', '', text)
    # 去掉所有空白字符（换行、空格、制表符）
    clean_text = "".join(text.split())
    return len(clean_text)

# --- 页面配置 ---
st.set_page_config(page_title="万能文案分镜提取器", layout="wide")

st.sidebar.title("⚙️ API 与模型配置")
api_key = st.sidebar.text_input("1. 输入 API Key", type="password")
base_url = st.sidebar.text_input("2. 中转地址", value="https://blog.tuiwen.xyz/v1/chat/completion")
# 注意：标准的 OpenAI SDK base_url 通常不需要包含 /chat/completions
# 如果你的接口特殊，代码中已做处理
standard_url = base_url.replace("/chat/completions", "").replace("/chat/completion", "")

model_id = st.sidebar.text_input("3. Model ID (模型名称)", value="gpt-4o", help="例如: gpt-4o, claude-3-5-sonnet, deepseek-chat")

st.sidebar.divider()
st.sidebar.info("""
**分镜准则：**
1. 单行 < 35 字符（约 5 秒）
2. 动作/场景/对话切换即断行
3. 严禁遗漏、增删任何原文文字
""")

# --- 主界面 ---
st.title("🎬 万能文案自动分镜系统")
st.caption("适配电影解说、短视频脚本拆解，支持字数完整性校验")

uploaded_file = st.file_uploader("📂 请选择本地 TXT 文案文件", type=['txt'])

if uploaded_file is not None:
    # 1. 处理输入文本
    raw_content = uploaded_file.getvalue().decode("utf-8")
    # 强制去除段落和空格，合成长文本，防止AI参考原格式
    merged_content = "".join(raw_content.split())
    input_char_count = len(merged_content)

    # 显示字数面板
    st.subheader("📊 文案字数统计面板")
    col_in, col_out, col_status = st.columns(3)
    col_in.metric("原文总字数", f"{input_char_count} 字")

    st.divider()

    if st.button("🚀 开始自动化深度分镜"):
        if not api_key:
            st.error("请先在左侧输入 API Key")
        else:
            try:
                # 初始化客户端
                client = OpenAI(api_key=api_key, base_url=standard_url)
                
                with st.spinner('AI 正在逐字扫描并重构分镜...'):
                    # --- 核心系统指令 ---
                    system_prompt = """你是一个顶级的电影解说分镜师。我会给你一段没有任何分段的文本，请执行以下操作：

1. **逐字理解**：理解文本的情节、对话、动作。
2. **逻辑拆分**：根据以下三个原则切换到下一个分镜（新的一行）：
   - 场景切换（环境变了）
   - 动作画面改变（角色做了一个新动作）
   - 角色对话切换（换人说话了）
3. **字数约束**：为了保证音频同步，每一行分镜的文案严禁超过 35 个字符。如果原句太长，请在不改变任何文字的前提下，按语义逻辑物理拆分为多行。
4. **零遗漏原则**：严禁遗漏原文中的任何一个字、一句话！严禁修改原文结构！严禁添加任何解释词或废话！
5. **纯净输出**：直接输出编号分镜列表（1.内容 2.内容），不要输出任何前言、总结或分析。
6. **忽略原结构**：彻底无视用户上传文本中可能的原始换行，必须根据语义逻辑重新生成。"""

                    # 调用 AI
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请处理以下文本，严格执行零遗漏和35字限制要求：\n\n{merged_content}"}
                        ],
                        temperature=0,  # 设为0以保证最高严谨度，不乱发挥
                    )

                    result = response.choices[0].message.content
                    output_char_count = count_pure_text(result)

                    # 渲染字数面板结果
                    col_out.metric("分镜后文案字数", f"{output_char_count} 字")
                    
                    diff = output_char_count - input_char_count
                    if diff == 0:
                        col_status.success("✅ 100% 完整对齐")
                    else:
                        col_status.error(f"⚠️ 字数不符（误差: {diff} 字）")
                        st.warning("提示：字数减少通常意味着模型‘偷懒’删减了内容，建议更换更强的模型（如 Claude-3-5-Sonnet）重新尝试。")

                    # 显示分镜结果
                    st.subheader("📜 分镜脚本结果")
                    st.text_area("可直接复制内容", value=result, height=600)
                    
                    st.download_button(
                        label="💾 下载分镜脚本",
                        data=result,
                        file_name="storyboard_output.txt",
                        mime="text/plain"
                    )

            except Exception as e:
                st.error(f"处理过程中出现错误：{str(e)}")

# --- 底部指引 ---
st.divider()
st.info("💡 **部署建议**：将此文件命名为 `app.py`，并在同级目录创建 `requirements.txt` (写入 `streamlit` 和 `openai`)，即可一键发布到 Streamlit Cloud。")
