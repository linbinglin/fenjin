import streamlit as st
from openai import OpenAI
import re

# --- 页面基础配置 ---
st.set_page_config(
    page_title="AI文案分镜助手 Pro",
    page_icon="🎬",
    layout="wide"
)

# --- 侧边栏：API 配置 ---
with st.sidebar:
    st.header("⚙️ 参数配置")
    
    api_key = st.text_input("API Key", type="password", placeholder="sk-xxxxxxxx")
    
    base_url = st.text_input(
        "Base URL (中转接口地址)", 
        value="https://blog.tuiwen.xyz/v1",
        help="通常填写到 /v1 即可，系统会自动处理后续路径"
    )
    
    # 模型选择
    model_options = [
        "gpt-4o",
        "deepseek-chat", 
        "claude-3-5-sonnet-20240620",
        "gemini-pro",
        "grok-beta",
        "doubao-pro-32k",
        "gpt-3.5-turbo"
    ]
    
    selected_model = st.selectbox("选择模型 ID", model_options, index=0)
    
    custom_model_check = st.checkbox("手动输入模型ID")
    if custom_model_check:
        model_id = st.text_input("请输入自定义模型ID", value=selected_model)
    else:
        model_id = selected_model

    st.markdown("---")
    st.info("💡 **分镜逻辑**：\n1. 角色/场景/动作改变 -> 换行\n2. 35字/行 -> 强制拆分\n3. 严禁删减原文")

# --- 辅助函数 ---

def clean_text_for_ai(text):
    """
    预处理：去除原文所有换行符和多余空格，
    把文本变成'一坨'，防止AI直接抄原有段落。
    """
    # 去除换行符
    text = text.replace("\n", "").replace("\r", "")
    # 去除多余的空格（可选，视具体需求而定，这里保留单个空格以防英文连在一起，如果是纯中文可以直接strip）
    return text.strip()

def calculate_pure_text_len(text, is_output=False):
    """
    计算有效字数。
    如果是分镜输出结果，需要去除 '1.', '2.' 这种序号和换行符，
    只计算纯文案内容的长度，以便和原文对比。
    """
    if not text:
        return 0
        
    if is_output:
        # 正则逻辑：
        # 1. 去除行首的数字和点 (例如 "1. ")
        # 2. 去除换行符
        # 3. 去除首尾空格
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # 替换掉 "数字." 或 "数字、" 开头的部分
            clean_line = re.sub(r'^\d+[\.|、]\s*', '', line)
            cleaned_lines.append(clean_line)
        return len("".join(cleaned_lines))
    else:
        # 原文直接计算长度
        return len(text)

# --- 主页面 ---
st.title("🎬 智能文案分镜生成器 (防漏词版)")

# 1. 文件上传区
uploaded_file = st.file_uploader("📂 第一步：上传TXT剧本", type=['txt'])

if uploaded_file is not None:
    # 读取原始内容
    raw_content = uploaded_file.read().decode("utf-8")
    
    # --- 新增功能：文本“拍扁”处理 ---
    # 强制去除段落，让AI无法偷懒
    flat_content = clean_text_for_ai(raw_content)
    
    # 计算原文有效字数
    input_len = len(flat_content)

    # --- 新增功能：字数面板 (输入) ---
    st.markdown("### 📊 字数统计面板")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="📄 原文有效字数", value=f"{input_len} 字", help="已去除所有换行符和段落格式")
    
    # 显示处理后的文本预览（让用户知道AI看到的是什么）
    with st.expander("👁️ 点击查看发送给AI的纯文本（已去格式）"):
        st.code(flat_content, language=None) # 使用code块展示，避免自动换行干扰视觉

    # 2. 生成按钮
    st.markdown("---")
    if st.button("🚀 开始AI分镜拆解", type="primary"):
        if not api_key:
            st.error("🚫 请先在左侧侧边栏输入 API Key")
        else:
            # 系统提示词 (System Prompt)
            system_prompt = """
            你是一个专业的电影解说分镜师。
            任务：将用户提供的【纯文本】按逻辑拆解为分镜脚本。
            
            【严重警告】：
            1. 用户提供的文本已经去除了格式，你必须根据语义重新断句。
            2. **严禁遗漏**：输出的总字数必须与原文高度一致，不能少一个字，也不能随意改词。
            3. **严禁添加**：不要添加任何原文没有的描述词。
            
            【分镜拆分逻辑】：
            1. **强制换行条件**：
               - 角色切换（A说话转B说话）
               - 场景切换（地点/时间变化）
               - 动作画面大幅改变
            2. **时间对齐（重点）**：
               - 每个分镜代表约5秒画面。
               - **单行文案严格限制在35个字符以内**。
               - 如果一句话超过35字，必须在语义通顺处强制切分到下一行（下一分镜）。
            
            【输出格式】：
            请严格只输出分镜内容，每行一个，带数字序号：
            1.文案内容...
            2.文案内容...
            """

            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                output_placeholder = st.empty()
                full_response = ""

                # 发起请求
                with st.spinner(f"🤖 AI ({model_id}) 正在重组分镜，请勿刷新页面..."):
                    stream = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文本进行分镜：\n\n{flat_content}"}
                        ],
                        stream=True,
                        temperature=0.1 # 降低温度，让AI更严谨，减少胡乱发挥
                    )

                    # 流式输出
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            content = chunk.choices[0].delta.content
                            full_response += content
                            output_placeholder.text_area("分镜生成结果", value=full_response + "▌", height=600)
                    
                    # 最终显示（移除光标）
                    output_placeholder.text_area("分镜生成结果", value=full_response, height=600)

                # --- 新增功能：输出字数核对 ---
                output_len = calculate_pure_text_len(full_response, is_output=True)
                diff = output_len - input_len
                
                with col2:
                    st.metric(
                        label="🎬 分镜有效字数 (不含序号)", 
                        value=f"{output_len} 字", 
                        delta=f"{diff} 字 (误差)",
                        delta_color="off" if abs(diff) == 0 else "inverse",
                        help="计算结果已自动剔除 '1.' 等序号和换行符"
                    )

                # 结果校验提示
                if abs(diff) > 5:
                    st.warning(f"⚠️ 警告：字数差异较大（差了 {abs(diff)} 字）。请检查AI是否遗漏了内容或产生了幻觉。")
                elif diff == 0:
                    st.success("✅ 完美：分镜字数与原文完全一致！")
                else:
                    st.info("ℹ️ 提示：字数有微小差异，通常是标点符号处理导致的，属正常范围。")

                # 下载按钮
                st.download_button(
                    label="📥 下载分镜脚本 (.txt)",
                    data=full_response,
                    file_name="分镜脚本.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error(f"❌ 发生错误：{str(e)}")
                st.markdown("##### 排查建议：")
                st.markdown("- 检查 API Key 是否正确")
                st.markdown("- 检查 Base URL 格式（通常以 `/v1` 结尾）")
                st.markdown("- 尝试切换模型 ID")

else:
    st.info("👈 请在左侧配置 API，并上传 TXT 文件开始使用")
