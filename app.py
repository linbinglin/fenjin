import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="AI电影解说分镜无损系统", layout="wide")

# --- 初始化 Session State ---
if 'original_text' not in st.session_state:
    st.session_state.original_text = ""
if 'editable_storyboard' not in st.session_state:
    st.session_state.editable_storyboard = ""
if 'final_results' not in st.session_state:
    st.session_state.final_results = []
if 'current_batch' not in st.session_state:
    st.session_state.current_batch = 0

# --- 侧边栏 ---
st.sidebar.title("🛠️ 导演配置中心")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("中转地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.title("🎬 电影解说无损分镜专家")
st.info("说明：先上传文案进行【第一步分镜】，确认无误并输入角色设定后，再进行【第二步描述】。")

# ================= 第一阶段：无损分镜切割 =================
st.header("Step 1: 文本切割与节奏对齐")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    # 读取内容并彻底抹除所有空格换行，形成纯字符流
    raw_content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    clean_raw = re.sub(r'\s+', '', raw_content).strip()
    st.session_state.original_text = clean_raw
    
    if st.button("📽️ 启动智能无损分镜"):
        if not api_key:
            st.error("请配置 API Key")
        elif not clean_raw:
            st.error("上传的文件内容为空")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 将系统指令和内容合并，防止接口报“空对话”错误
                user_message = f"""你是一个顶级的电影解说分镜导演。你的任务是进行【无损切割】。
                
【核心准则】：
1. 绝对严禁删除、添加、修改原文中的任何一个字或标点。
2. 文本顺序必须与原文完全一致。
3. 你的工作仅是在合适的逻辑点插入换行符。

【分镜切割要求】：
1. **长度指标**：每个分镜文案严格控制在 30-38 字符之间。绝对严禁超过40个字符。
2. **逻辑切分点**：优先在角色对话、场景变换、重大动作改变处切分。
3. **平衡感**：如果相邻两句话加起来不超过38字且动作连贯，请合并为一行，不要分得太碎。

请对以下文本进行切割处理，直接输出分镜结果（每行一个分镜）：
{clean_raw}"""

                with st.spinner("AI正在进行精密切割..."):
                    # 使用 messages 列表，同时包含 system 和 user，确保兼容性
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你是一个严格的分镜导演，只负责对文本进行换行切割。"},
                            {"role": "user", "content": user_message}
                        ],
                        temperature=0
                    )
                    st.session_state.editable_storyboard = response.choices[0].message.content
                    st.session_state.final_results = []
                    st.session_state.current_batch = 0
            except Exception as e:
                st.error(f"处理失败: {str(e)}")

# 预览与人工微调区
if st.session_state.editable_storyboard:
    col_edit, col_stat = st.columns([3, 2])
    
    with col_edit:
        st.subheader("📝 分镜编辑（实时同步）")
        edited_text = st.text_area("分镜文案草稿", value=st.session_state.editable_storyboard, height=450)
        st.session_state.editable_storyboard = edited_text

    with col_stat:
        st.subheader("📊 质量监控看板")
        # 实时解析
        lines = [l.strip() for l in edited_text.split('\n') if l.strip()]
        full_recombined = ""
        processed_lines = []
        
        for i, line in enumerate(lines):
            # 自动去掉序号前缀，计算纯文案长度
            content = re.sub(r'^\d+[\.、\s]+', '', line)
            full_recombined += content
            char_len = len(content)
            
            if char_len > 40: status = "🔴 太挤(超5s)"
            elif char_len < 15: status = "🟡 太碎"
            else: status = "🟢 理想"
            
            processed_lines.append({"分镜": i+1, "字数": char_len, "状态": status})
        
        # 无损校验
        orig_len = len(st.session_state.original_text)
        new_len = len(full_recombined)
        
        if orig_len == new_len:
            st.success(f"✅ 无损检测通过 ({orig_len}字)")
        else:
            st.error(f"⚠️ 丢字/多字预警！原:{orig_len}字 -> 现:{new_len}字")
            st.info("提示：请检查是否有文字在编辑时被意外删改。")
            
        st.dataframe(pd.DataFrame(processed_lines), use_container_width=True)

    st.divider()

    # ================= 第二阶段：分步描述生成 =================
    st.header("Step 2: 生成画面与视频描述")
    
    char_desc = st.text_area("输入角色视觉设定 (Midjourney生图关键)", 
                            placeholder="描述角色外貌、衣着细节、风格。例如：赵清月：清冷美人，肤白如雪，穿着白色绫罗纱衣。",
                            key="char_desc_input")
    
    if char_desc:
        # 获取最终确认的列表
        final_list = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in st.session_state.editable_storyboard.split('\n') if l.strip()]
        total = len(final_list)
        idx = st.session_state.current_batch
        size = 20
        end = min(idx + size, total)

        if idx < total:
            if st.button(f"🎨 生成第 {idx+1} - {end} 组导演提示词"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_data = ""
                    for i, text in enumerate(final_list[idx:end]):
                        batch_data += f"分镜{idx+i+1}：{text}\n"
                    
                    prompt = f"""你现在是电影视觉导演。请为以下分镜生成MJ和即梦AI描述。

角色背景设定：
{char_desc}

任务要求：
1. **画面描述 (MJ)**：描述静态场景、人物外貌、着装细节、景别（特写/中景等）、光影。**不准描述任何动作行为**。
2. **视频生成 (即梦AI)**：描述5秒内的动作流。描述人物神态变化、肢体位移、镜头移动（如：镜头缓慢推向面部特写）。使用**短句堆砌**。
3. **一致性**：必须严格遵循角色设定，确保多组分镜中人物外貌统一。

待处理分镜组：
{batch_data}"""

                    with st.spinner("正在构思画面细节..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        st.session_state.final_results.append(response.choices[0].message.content)
                        st.session_state.current_batch = end
                        st.rerun()
                except Exception as e:
                    st.error(f"生成失败: {str(e)}")
        else:
            st.success("🏁 所有分镜描述生成完毕！")

        for r_idx, r_text in enumerate(st.session_state.final_results):
            with st.expander(f"📦 批次 {r_idx+1} 生成结果", expanded=True):
                st.text_area(f"Result_{r_idx+1}", r_text, height=400)
