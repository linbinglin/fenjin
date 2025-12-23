import streamlit as st
from openai import OpenAI
import io
import math

st.set_page_config(page_title="电影解说分镜导演系统", layout="wide")

# --- 初始化 Session State ---
if 'all_shots' not in st.session_state:
    st.session_state.all_shots = []  # 存储纯分镜文案列表
if 'current_batch_idx' not in st.session_state:
    st.session_state.current_batch_idx = 0 # 当前处理到第几组
if 'descriptions' not in st.session_state:
    st.session_state.descriptions = [] # 存储生成的详细描述

# --- 侧边栏：API配置 ---
st.sidebar.title("⚙️ 配置中心")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

# --- 主界面 ---
st.title("🎬 电影解说全流程分镜导演系统")

# 输入区
col_a, col_b = st.columns(2)
with col_a:
    uploaded_file = st.file_uploader("1. 上传文案 (TXT)", type=['txt'])
with col_b:
    char_desc = st.text_area("2. 核心角色设定 (必填)", 
                            placeholder="角色名：外貌细节、服装样式...\n例如：林凡：25岁，黑色冲锋衣，眼神冷酷。", 
                            height=100)

# --- 第一步：分镜拆解 ---
if uploaded_file and char_desc:
    raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    
    if st.button("Step 1: 生成/刷新分镜预览"):
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            # 强制分镜Prompt
            seg_prompt = f"""你是一个电影剪辑师。请忽略原文段落，将以下文本重新拆解为分镜。
规则：
1. 每组分镜文案严格禁止超过40个字符（约5秒音频）。
2. 只要有：场景切换、角色对话切换、核心动作改变，必须立即拆分为下一组。
3. 严禁改动、遗漏原文任何文字。
4. 输出格式：仅输出序号和文案，每行一个。例如：1.文案内容
文本内容：\n{raw_text}"""
            
            with st.spinner("正在进行物理拆分分镜..."):
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": seg_prompt}],
                    temperature=0.3
                )
                res_text = response.choices[0].message.content
                # 简单解析结果存入session
                st.session_state.all_shots = [line for line in res_text.split('\n') if line.strip()]
                st.session_state.current_batch_idx = 0
                st.session_state.descriptions = []
        except Exception as e:
            st.error(f"拆解失败: {e}")

# --- 结果展示与深度描述生成 ---
if st.session_state.all_shots:
    st.divider()
    st.subheader("📋 分镜预览 (共计 {} 组)".format(len(st.session_state.all_shots)))
    
    # 预览区域
    with st.expander("查看所有分镜文案", expanded=True):
        for shot in st.session_state.all_shots:
            st.write(shot)

    st.divider()
    st.subheader("🎨 深度画面描述生成 (每批20组)")

    # 确定当前批次
    start_idx = st.session_state.current_batch_idx
    end_idx = min(start_idx + 20, len(st.session_state.all_shots))
    current_batch_list = st.session_state.all_shots[start_idx:end_idx]

    if start_idx < len(st.session_state.all_shots):
        if st.button(f"生成第 {start_idx+1} - {end_idx} 组的画面描述"):
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 深度描述Prompt
                desc_prompt = f"""你是一个视觉导演，请为以下分镜生成Midjourney和即梦AI提示词。
角色设定：{char_desc}

要求：
1. 每一组分镜必须包含：[分镜文案]、[画面描述]、[视频生成]。
2. [画面描述]针对Midjourney：描述场景、人物外貌、着装、光影，严禁描述动作。
3. [视频生成]针对即梦AI：描述镜头语言、微表情、核心动作。采用短句堆砌，单焦原则（一个分镜1个动作）。
4. 确保场景和服装在各分镜间的一致性。

待处理分镜：
{chr(10).join(current_batch_list)}"""

                with st.spinner("AI正在构思画面细节..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": desc_prompt}],
                        temperature=0.7
                    )
                    batch_res = response.choices[0].message.content
                    st.session_state.descriptions.append(batch_res)
                    st.session_state.current_batch_idx = end_idx
                    st.rerun() # 刷新显示结果
            except Exception as e:
                st.error(f"描述生成失败: {e}")
    else:
        st.success("✅ 所有分镜描述已生成完毕！")

    # 显示已生成的描述
    for idx, desc in enumerate(st.session_state.descriptions):
        st.markdown(f"### 📦 第 {idx+1} 批次结果")
        st.text_area(f"批次 {idx+1} 文本 (可复制)", desc, height=400)

    if st.session_state.current_batch_idx > 0 and st.session_state.current_batch_idx < len(st.session_state.all_shots):
        if st.button("继续生成下20组描述"):
            st.rerun()
