import streamlit as st
import requests
import json
import re

# 设置页面配置
st.set_page_config(page_title="全能文案·电影感分镜系统", layout="wide")

# --- 侧边栏配置 ---
with st.sidebar:
    st.title("⚙️ 导演引擎配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.info("""
    **V1.1 视觉切换准则：**
    1. 人称切换必须断开。
    2. 动作完成必须切换。
    3. 场景转换强制换行。
    4. 严控35字/分镜。
    """)

# --- 主界面 ---
st.title("🎬 全能文案·电影感分镜系统 (V1.1)")

uploaded_file = st.file_uploader("选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    # 读取原文并预处理：去除多余空行，合并为纯连续文本
    raw_content = uploaded_file.read().decode("utf-8")
    clean_content = "".join(raw_content.split()) # 彻底抹除原段落结构，防止AI偷懒
    
    col1, col2, col3 = st.columns(3)
    col1.metric("原文总字数", len(clean_content))
    
    if st.button("🚀 启动视觉无损分镜"):
        if not api_key:
            st.error("请输入 API Key")
        else:
            # 构建严谨的 Prompt
            prompt = f"""
            你是一个极其严谨的电影解说分镜师。
            任务：将以下文案转换为分镜脚本。
            
            【硬性指令】
            1. 逐字逐句理解，不可遗漏、添加、或更改任何一个字。
            2. 抹除原有段落，重新按照视觉逻辑切分。
            3. 每行一个分镜，编号格式为“数字.”。
            4. 触发切分条件：
               - 角色对话切换。
               - 场景地点改变。
               - 核心动作完成（如：进门、坐下、回头）。
            5. 节奏限制：每个分镜文案绝对禁止超过35个汉字（为了对齐5秒音频）。

            【输入原文】
            {clean_content}

            【输出格式示例】
            1.文案内容
            2.文案内容
            """

            try:
                with st.spinner("正在进行视觉单元规划..."):
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    data = {
                        "model": model_id,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3 # 降低随机性，保证严谨
                    }
                    
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data)
                    result = response.json()
                    output_text = result['choices'][0]['message']['content']
                    
                    # --- 后处理与统计 ---
                    lines = [l for l in output_text.split('\n') if l.strip()]
                    processed_content = "".join([re.sub(r'^\d+\.', '', l).strip() for l in lines])
                    offset = len(clean_content) - len(processed_content)
                    
                    # --- 结果展示 ---
                    col2.metric("生成分镜总数", f"{len(lines)} 组")
                    col3.metric("偏移值 (差值)", f"{offset} 字", delta_color="inverse" if offset != 0 else "normal")
                    
                    if offset != 0:
                        st.warning(f"⚠️ 警告：检测到字符偏移！原文{len(clean_content)}字，生成后剩余{len(processed_content)}字。请检查是否有遗漏。")

                    st.subheader("📝 视觉分镜编辑器 (无损还原)")
                    
                    # 实时节奏分析与长度监控
                    for idx, line in enumerate(lines):
                        content_only = re.sub(r'^\d+\.', '', line).strip()
                        char_count = len(content_only)
                        
                        col_l, col_r = st.columns([0.8, 0.2])
                        with col_l:
                            st.text_area(f"分镜 {idx+1}", value=line, height=70, key=f"shot_{idx}")
                        with col_r:
                            if char_count > 35:
                                st.error(f"字数: {char_count} (超标)")
                            else:
                                st.success(f"字数: {char_count}")

            except Exception as e:
                st.error(f"处理出错：{str(e)}")
