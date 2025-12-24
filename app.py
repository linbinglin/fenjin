import streamlit as st
import requests
import time

# --- 页面配置 ---
st.set_page_config(page_title="精密分镜助理 Pro", layout="wide")
st.title("🎬 自动文案分镜拆解系统 (分段增强版)")

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 配置中心")
    api_url = st.text_input("API 地址", value="https://blog.tuiwen.xyz/v1/chat/completions")
    api_key = st.text_input("API Key", type="password")
    selected_model = st.text_input("Model ID", value="deepseek-chat")
    
    st.divider()
    chunk_size = st.slider("每批处理字符数", 500, 3000, 1500, help="针对长文案，建议分段处理防止超时")
    st.info("较真提醒：检测到长文案时，系统将自动开启分段处理逻辑。")

# --- 严格的分镜指令 ---
SYSTEM_PROMPT = """你是一个极其严谨、较真的电影解说分镜专家。
你的任务是将用户提供的【文本片段】重新排列为【分镜脚本】。

执行准则：
1. **零损耗原则**：禁止修改、添加或删除原文任何字。必须保证原文的所有文字按顺序完整出现。
2. **强制分镜逻辑**：
   - 场景转换、角色对话切换、画面动作改变时，必须另起一个分镜序号。
   - 每个分镜的文字长度严格控制在 15-35 个字符之间。
3. **消除段落干扰**：将输入视为连续文本流处理。
4. **输出格式**：仅输出带序号的分镜列表，例如：
   1.分镜内容
   2.分镜内容
"""

def process_chunk(text, start_index, retry_count=3):
    """单块文本处理函数，带重试逻辑"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"这是剧本的第 {start_index} 部分，请严格执行分镜处理：\n\n{text}"}
        ],
        "temperature": 0.2
    }
    
    for i in range(retry_count):
        try:
            # 增加到 120 秒超时，以应对慢速中转接口
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            if i == retry_count - 1:
                return f"⚠️ 该段处理失败：{str(e)}"
            time.sleep(2) # 失败重试间隔

# --- 主界面 ---
uploaded_file = st.file_uploader("选择本地 .txt 文案文件", type=['txt'])

if uploaded_file is not None:
    original_text = uploaded_file.read().decode("utf-8").replace("\n", " ").strip()
    full_length = len(original_text)
    
    st.write(f"📊 文案总长度：{full_length} 字符 | 预计分段：{-(full_length // -chunk_size)} 段")

    if st.button("🚀 开始自动化精密分镜"):
        if not api_key:
            st.error("请先输入 API Key")
        else:
            final_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # --- 分段逻辑 ---
            chunks = [original_text[i:i+chunk_size] for i in range(0, full_length, chunk_size)]
            
            output_area = st.empty() # 用于实时滚动显示结果
            accumulated_text = ""
            
            for idx, chunk in enumerate(chunks):
                status_text.text(f"正在处理第 {idx+1}/{len(chunks)} 段...")
                
                chunk_result = process_chunk(chunk, idx + 1)
                accumulated_text += chunk_result + "\n"
                
                # 实时更新 UI
                output_area.text_area("实时生成预览", accumulated_text, height=400)
                
                progress = (idx + 1) / len(chunks)
                progress_bar.progress(progress)
            
            status_text.success("✅ 全部分镜处理完成！")
            st.download_button("📥 导出完整分镜脚本", accumulated_text, file_name="storyboard_full.txt")
