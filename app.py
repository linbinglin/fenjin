import streamlit as st
import requests
import time

# --- 页面配置 ---
st.set_page_config(page_title="精密分镜助理 Pro Max", layout="wide")
st.title("🎬 电影解说精密分镜系统")

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 导演级配置")
    api_url = st.text_input("API 地址", value="https://blog.tuiwen.xyz/v1/chat/completions")
    api_key = st.text_input("API Key", type="password")
    selected_model = st.text_input("Model ID", value="grok-4.1") # 默认您习惯的模型
    
    st.divider()
    chunk_size = st.slider("每批处理字符数", 500, 3000, 1500)
    st.warning("较真准则：每个分镜必须控制在 20-35 字之间，以匹配 5 秒黄金剪辑律。")

# --- 深度优化的 AI 指令 ---
SYSTEM_PROMPT = """你是一个顶级的电影解说导演和首席剪辑师。你的任务是将文学稿件转化为高水准的【分镜脚本】。

请严格遵守以下【较真协议】：

1. **视听对齐原则（核心）**：
   - 每一个分镜的文字，对应的语音时长必须接近 5 秒。
   - 【硬性约束】：每段文字必须在 20 到 35 个字符之间。
   - 【操作逻辑】：如果一句话太短（如“他笑了”），必须与其后的描写合并。如果一句话太长（超过35字），必须在逻辑停顿处切分。

2. **分镜切分逻辑**：
   - 只有满足以下任一条件，才允许开启新的一行（新分镜）：
     a) 当前累计文字已达到 25-35 字。
     b) 故事发生了物理空间的场景切换。
     c) 角色发生了明显的身份/时空转换（如“第一世”到“第二世”）。
     d) 出现了全新的角色对白。

3. **零损耗规范**：
   - 严禁删除、修改、润色原文中的任何一个字符。
   - 严禁添加任何描述语、开场白或括号说明。

4. **禁止偷懒**：
   - 不要直接沿用原文的段落。请将原文视为一个没有空格和换行的长字符串，由你重新根据“25-35字/5秒”的节奏感进行物理切分。

输出格式示例：
1.第一段分镜文字（20-35字）
2.第二段分镜文字（20-35字）
...
"""

def process_chunk(text, idx):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # 在发送给AI前，彻底抹除原文的排版痕迹，迫使AI重构
    flat_text = text.replace("\n", "").replace("\r", "").replace(" ", "").strip()
    
    payload = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"请对以下文本流进行导演级分镜处理（当前处理第{idx}部分）：\n\n{flat_text}"}
        ],
        "temperature": 0.1 # 极端严谨模式
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ 错误：{str(e)}"

# --- 主界面 ---
uploaded_file = st.file_uploader("选择本地 .txt 文案文件", type=['txt'])

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    
    if st.button("🚀 开始自动化精密分镜"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            # 自动分段处理逻辑
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            all_output = ""
            
            p_bar = st.progress(0)
            for i, chunk in enumerate(chunks):
                with st.spinner(f"正在以导演思维解析第 {i+1} 段..."):
                    res = process_chunk(chunk, i+1)
                    all_output += res + "\n"
                    p_bar.progress((i + 1) / len(chunks))
            
            st.subheader("🎬 优化后的分镜结果")
            st.text_area("生成的脚本：", all_output, height=500)
            
            # 较真校验：统计每行字数并给出警告
            lines = [line for line in all_output.split('\n') if line.strip()]
            bad_lines = [l for l in lines if len(l.split('.', 1)[-1]) > 35 or len(l.split('.', 1)[-1]) < 15]
            if bad_lines:
                st.warning(f"较真提示：检测到 {len(bad_lines)} 处分镜可能存在时长不合规，请人工微调。")
