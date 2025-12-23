import streamlit as st
from openai import OpenAI
import re

# --- 页面配置 ---
st.set_page_config(
    page_title="AI 双重精修分镜助手",
    page_icon="🎬",
    layout="wide"
)

# --- 侧边栏：设置 ---
st.sidebar.header("⚙️ 设置中心")
default_base_url = "https://blog.tuiwen.xyz/v1"
base_url = st.sidebar.text_input("API Base URL", value=default_base_url)
api_key = st.sidebar.text_input("API Key", type="password")

st.sidebar.subheader("🤖 模型选择")
# 建议使用逻辑能力强的模型进行二次检查
model_options = ["gpt-4o", "deepseek-chat", "claude-3-5-sonnet-20240620", "gemini-pro"]
selected_list_model = st.sidebar.selectbox("选择模型", model_options, index=0)
custom_model_input = st.sidebar.text_input("或手动输入模型 ID", value="")
final_model = custom_model_input if custom_model_input.strip() else selected_list_model

# --- 文本清洗函数 ---
def clean_text_structure(text):
    text = text.replace('\n', '').replace('\r', '').replace('\t', '')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# --- 第一步：粗分镜 Prompt ---
def get_draft_prompt():
    return """
    你是一名编剧。请阅读用户提供的纯文本剧情，进行【第一轮粗略分镜】。
    
    【任务目标】
    仅根据**剧情走向**和**角色对话**进行分段。
    
    【标准】
    1. 哪怕一句话很长，只要是同一个人连贯在说，或者同一个连续动作，就先放在一行。
    2. 只有在**非常明显**的角色切换或场景大跳跃时才换行。
    3. 绝对保留原文，不要修改一个字。
    
    请输出带序号的粗分镜列表。
    """

# --- 第二步：精修 Prompt (核心) ---
def get_refine_prompt():
    return """
    你是一名苛刻的【视觉导演】。你的任务是审查并修改【第一轮粗分镜】。
    
    【痛点分析】
    第一轮分镜的问题是：**很多分镜太长，包含的动作太多，一张画面根本做不完（视觉过载）。**
    
    【你的工作 - 必须执行以下修改】
    请逐行检查粗分镜，如果发现以下情况，必须**强制拆分**为多个新分镜：
    1. **字数过载**：如果单行超过 40 个字符，必须在逗号或句号处拆开。
    2. **动作堆叠**：例如“A做了B，然后又去做了C，最后看了D”。这必须拆分为3个分镜。
    3. **视觉变化**：如果一句话前半句是“全景”，后半句明显需要“特写”，请拆开。
    
    【示例】
    输入(粗分镜)：1. 我把僧人端来的粥饭全给了母亲施粥的将军府老妇人让人领我过来问怎么不吃
    修正(你输出)：
    1.我把僧人端来的粥饭全给了母亲
    2.施粥的将军府老妇人，让人领我过来问
    3.都饿成人干了怎么不吃

    【最终输出要求】
    1. 输出修改后的完整分镜列表。
    2. 重新排列数字序号 (1. 2. 3...)。
    3. **严禁修改原文文字**，严禁删减，只能进行“回车切分”操作。
    """

# --- 主界面 ---
st.title("🎬 AI 双重逻辑分镜系统 (Draft & Refine)")
st.markdown("""
**工作原理：**
1. **Pass 1 (粗剪)**：AI 先通读全文，理清故事脉络，生成基础分镜。
2. **Pass 2 (精修)**：AI 回头检查第一版，专门寻找**“太长”、“太挤”、“无法视觉化”**的段落，进行二次拆解。
""")

uploaded_file = st.file_uploader("上传文案 (.txt)", type=['txt'])

if uploaded_file and api_key:
    # 0. 预处理
    raw_content = uploaded_file.read().decode("utf-8")
    merged_content = clean_text_structure(raw_content)
    
    st.info("文案已清洗，准备进行双重处理...")

    if st.button("🚀 开始双重分镜处理", type="primary"):
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        # 使用 st.status 显示处理步骤
        with st.status("正在进行导演级处理...", expanded=True) as status:
            
            # --- 第一轮：粗分镜 ---
            status.write("📝 第一步：正在进行剧情粗剪（理解故事结构）...")
            draft_response = ""
            try:
                stream1 = client.chat.completions.create(
                    model=final_model,
                    messages=[
                        {"role": "system", "content": get_draft_prompt()},
                        {"role": "user", "content": merged_content}
                    ],
                    stream=True,
                    temperature=0.3
                )
                
                draft_placeholder = st.empty()
                for chunk in stream1:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        draft_response += content
                        # 这里可以选择不展示Draft，或者折叠展示，为了不干扰用户，我们暂存不展示太长
                
                status.write("✅ 第一步完成。")
                
                # --- 第二轮：精修 ---
                status.write("✂️ 第二步：正在进行视觉密度检查与拆分（二次修正）...")
                
                stream2 = client.chat.completions.create(
                    model=final_model,
                    messages=[
                        {"role": "system", "content": get_refine_prompt()},
                        {"role": "user", "content": f"这是第一轮的粗糙分镜，请对其进行精修拆分，确保视觉节奏合理：\n\n{draft_response}"}
                    ],
                    stream=True,
                    temperature=0.1 # 精修时温度要低，保证只拆分不改字
                )
                
                final_response = ""
                final_placeholder = st.empty()
                
                for chunk in stream2:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        final_response += content
                        final_placeholder.text_area("正在生成最终精修结果...", final_response, height=600)
                
                status.update(label="🎉 双重分镜处理完成！", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"发生错误: {e}")
                status.update(label="❌ 处理失败", state="error")

        # --- 结果展示区 ---
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            with st.expander("查看第一轮粗剪结果 (中间过程)"):
                st.text(draft_response)
        
        with col2:
            st.subheader("✅ 最终精修分镜")
            st.text_area("Final Output", final_response, height=600)
            
            st.download_button(
                label="📥 下载最终脚本",
                data=final_response,
                file_name="refined_storyboard.txt",
                mime="text/plain"
            )

elif not api_key:
    st.warning("👈 请先在左侧配置 API Key")
