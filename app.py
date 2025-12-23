import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# --- 1. 核心逻辑函数 ---
def get_clean_text(text):
    """提取纯文本，排除编号和空格，用于严苛对账"""
    if not text: return ""
    # 移除类似 1. 或 1、 的行首编号
    text = re.sub(r'^\s*\d+[\.、]\s*', '', text, flags=re.MULTILINE)
    # 移除所有空白符、换行
    return "".join(text.split())

def reindex_text(text):
    """手动微调后的序号重排系统"""
    lines = text.split('\n')
    valid_lines = []
    count = 1
    for line in lines:
        # 去掉原序号
        content = re.sub(r'^\s*\d+[\.、]\s*', '', line).strip()
        if content:
            valid_lines.append(f"{count}.{content}")
            count += 1
    return "\n".join(valid_lines)

# --- 2. 页面配置 ---
st.set_page_config(page_title="解说分镜 Pro V13", layout="wide")

# --- 3. 侧边栏配置 ---
with st.sidebar:
    st.title("⚙️ 引擎设置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    st.divider()
    st.info("💡 模式：V13 像素无损版\n特点：分段处理，强力纠偏")

# --- 4. 初始化 Session State ---
if 'final_storyboard' not in st.session_state:
    st.session_state.final_storyboard = ""
if 'original_text_clean' not in st.session_state:
    st.session_state.original_text_clean = ""

# --- 5. 主界面 ---
st.title("🎬 电影解说·分镜自动处理系统")
uploaded_file = st.file_uploader("📂 选择本地 TXT 文案", type=['txt'])

if uploaded_file:
    # 立即读取并锁定原始文字
    content = uploaded_file.getvalue().decode("utf-8")
    st.session_state.original_text_clean = "".join(content.split())
    input_len = len(st.session_state.original_text_clean)

    # 监控面板
    st.subheader("📊 逻辑监控看板")
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("原文总字数", f"{input_len} 字")

    # --- 6. AI 处理逻辑 ---
    if st.button("🚀 启动自动化分镜"):
        if not api_key:
            st.error("请在侧边栏配置 API Key")
        else:
            try:
                # 规范化 URL
                client = OpenAI(api_key=api_key, base_url=base_url.split('/chat')[0].strip())
                
                # 分段处理，每段 1000 字，防止幻觉
                text_full = st.session_state.original_text_clean
                chunks = [text_full[i:i+1000] for i in range(0, len(text_full), 1000)]
                
                results = []
                current_idx = 1
                prog = st.progress(0)
                
                for i, chunk in enumerate(chunks):
                    with st.spinner(f"正在处理第 {i+1}/{len(chunks)} 任务块..."):
                        prompt = f"""你是一个解说分镜搬运工。
要求：
1. 像素级还原原文，严禁增减、修改、重复、或润色！
2. 每行字数严格在 25-35 字之间，超过必须切断。
3. 对话切换、大动作必须换行。
4. 编号从 {current_idx} 开始。
待处理文本：
{chunk}"""

                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "system", "content": "直接输出分镜列表，严禁废话。"},
                                      {"role": "user", "content": prompt}],
                            temperature=0
                        )
                        chunk_res = response.choices[0].message.content.strip()
                        results.append(chunk_res)
                        
                        # 更新序号
                        nums = re.findall(r'(\d+)[\.、]', chunk_res)
                        if nums: current_idx = int(nums[-1]) + 1
                        prog.progress((i+1)/len(chunks))
                
                st.session_state.final_storyboard = "\n".join(results)
                st.success("分镜生成成功！")
            except Exception as e:
                st.error(f"处理出错：{str(e)}")

# --- 7. 编辑与校准区 ---
if st.session_state.final_storyboard:
    st.divider()
    st.subheader("✍️ 人工精修编辑器")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        # 编辑器
        edited_area = st.text_area(
            "可在下方手动增减内容（回车分镜，删除合并）：",
            value=st.session_state.final_storyboard,
            height=500,
            key="story_editor"
        )
        
        c1, c2 = st.columns(2)
        if c1.button("🔢 校准所有分镜序号"):
            st.session_state.final_storyboard = reindex_text(edited_area)
            st.rerun()
        
        c2.download_button("💾 下载分镜脚本", st.session_state.final_storyboard, "storyboard.txt")

    with col_right:
        # 实时统计
        processed_clean = get_pure_text(st.session_state.final_storyboard)
        processed_len = len(processed_clean)
        diff = processed_len - len(st.session_state.original_text_clean)
        
        lines = [l for l in st.session_state.final_storyboard.split('\n') if re.match(r'^\d+', l.strip())]
        
        st.metric("生成分镜总数", f"{len(lines)} 组")
        st.metric("还原总字数", f"{processed_len} 字")
        
        if diff == 0:
            st.success("✅ 字数完美对齐")
        else:
            st.error(f"❌ 字数偏差：{diff}")
            st.caption("正数为内容重复/脑补，负数为漏字。")

        # 节奏分析表
        analysis = []
        for i, line in enumerate(lines):
            txt = re.sub(r'^\d+[\.、]\s*', '', line)
            analysis.append({"镜": i+1, "字数": len(txt), "状态": "✅" if len(txt) <= 35 else "⚠️过长"})
        st.dataframe(pd.DataFrame(analysis), height=300, use_container_width=True)
