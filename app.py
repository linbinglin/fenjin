import streamlit as st
import requests
import json
import re
import pandas as pd

# 页面配置
st.set_page_config(page_title="导演引擎 V12 - 剧情驱动分镜", layout="wide")

# 侧边栏配置
with st.sidebar:
    st.header("🎬 导演引擎控制台")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="grok-4.1")
    
    st.divider()
    st.markdown("""
    ### 🎭 导演分镜准则：
    1. **剧情驱动**：分析文本的【起、承、转、合】，在叙事重心偏移时切换镜头。
    2. **动作闭环**：一个完整的动作描写（如：他翻身上马，扬长而去）视为一个镜头，不要从中掐断。
    3. **对话逻辑**：对话人切换时必换镜头；若一人长篇大论，按其表达的【意思转折点】切换。
    4. **节奏参考**：参考 30-40 字的语感节奏，但逻辑完整性高于字数限制。
    """)
    chunk_val = st.slider("处理窗口大小 (建议 1500)", 500, 3000, 1500)

# 主界面
st.title("🎥 剧情逻辑分镜系统")

if 'storyboard_data' not in st.session_state:
    st.session_state.storyboard_data = []
if 'raw_text_len' not in st.session_state:
    st.session_state.raw_text_len = 0

# 1. 文件上传
uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    # 彻底清除原有干扰格式
    clean_text = "".join(content.split())
    st.session_state.raw_text_len = len(clean_text)
    
    col_info, col_btn = st.columns([3, 1])
    col_info.info(f"📄 文本解析成功 | 总字数：{st.session_state.raw_text_len} 字")
    
    if col_btn.button("🚀 开始逻辑分析并生成分镜"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            # 采用较大的窗口，让AI有足够的剧情理解空间
            chunks = [clean_text[i:i+chunk_val] for i in range(0, len(clean_text), chunk_val)]
            
            all_shots = []
            progress = st.progress(0)
            
            for idx, chunk in enumerate(chunks):
                st.write(f"正在深度分析剧情第 {idx+1}/{len(chunks)} 块...")
                
                # 升级后的 Prompt：强调剧情理解，而非字数切分
                system_prompt = """你是一位资深的电影解说导演，精通剧本结构分析。
                你的任务是：将提供的文案流【无损】还原为逻辑严密的分镜脚本。

                工作流要求：
                1. 理解剧情：首先阅读整段文字，识别其中的角色、场景、核心动作。
                2. 逻辑分镜：
                   - 镜头切换点必须是：场景转移、角色互换、动作节奏变化、或情感转折处。
                   - 严禁机械化切分！一个分镜应包含一个完整的“视觉信息块”。
                3. 节奏控制：虽然不要死板限制字数，但请保持分镜文案在 20-45 字之间，以便后期配音与画面对齐。
                4. 无损还原：绝对严禁删改、总结原文。每一句话、每一个字都必须按顺序出现在分镜中。
                5. 格式：仅输出编号和内容，如：
                1. 内容...
                2. 内容...
                """
                
                try:
                    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                    payload = {
                        "model": model_id,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请深度阅读并逻辑化分镜：\n{chunk}"}
                        ],
                        "temperature": 0.2 
                    }
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                    chunk_result = response.json()['choices'][0]['message']['content']
                    
                    # 使用更稳健的正则表达式提取内容
                    lines = re.findall(r'\d+[.、\s]+(.*)', chunk_result)
                    if not lines: # 兜底逻辑
                         lines = chunk_result.strip().split('\n')
                    
                    all_shots.extend([l.strip() for l in lines if l.strip()])
                    
                except Exception as e:
                    st.error(f"处理出错: {str(e)}")
                
                progress.progress((idx + 1) / len(chunks))
            
            st.session_state.storyboard_data = all_shots

# 2. 结果可视化与稽核面板
if st.session_state.storyboard_data:
    # 数据计算
    processed_text = "".join(st.session_state.storyboard_data)
    processed_len = len(processed_text)
    diff = processed_len - st.session_state.raw_text_len
    
    # 顶部稽核数据卡片
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文总字数", f"{st.session_state.raw_text_len}")
    c2.metric("生成分镜数", f"{len(st.session_state.storyboard_data)} 组")
    c3.metric("处理后字数", f"{processed_len}")
    c4.metric("偏差值", f"{diff} 字", delta=diff, delta_color="inverse")

    # 左右布局
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("📝 分镜正文预览")
        # 允许用户在文本框微调
        full_script = "\n".join([f"{i+1}. {s}" for i, s in enumerate(st.session_state.storyboard_data)])
        st.text_area("分镜编辑器", full_script, height=600)

    with col_right:
        st.subheader("📊 视觉节奏监控")
        df = pd.DataFrame({
            "分镜序号": range(1, len(st.session_state.storyboard_data) + 1),
            "文案内容": st.session_state.storyboard_data,
            "字数": [len(s) for s in st.session_state.storyboard_data]
        })
        
        # 这里的状态逻辑不再是简单的报错，而是“节奏评估”
        def judge_rhythm(length):
            if length < 10: return "⚡ 快节奏"
            if 10 <= length <= 45: return "✅ 标准"
            return "🐢 慢镜头/需手动切分"

        df["建议状态"] = df["字数"].apply(judge_rhythm)
        st.dataframe(df, height=550, use_container_width=True)
        
        st.download_button("💾 下载最终脚本", full_script, file_name="director_final_script.txt")
