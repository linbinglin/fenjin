import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="AI全流程导演分镜系统", layout="wide")

# --- 初始化 Session State ---
if 'original_text' not in st.session_state: st.session_state.original_text = ""
if 'storyboard_draft' not in st.session_state: st.session_state.storyboard_draft = ""
if 'desc_batches' not in st.session_state: st.session_state.desc_batches = []
if 'batch_progress' not in st.session_state: st.session_state.batch_progress = 0

# --- 侧边栏配置 ---
st.sidebar.title("🎬 导演室设置")
api_key = st.sidebar.text_input("API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.title("🎥 电影解说全流程导演分镜系统")
st.caption("基于电影剪辑逻辑：在音频时长限制内，寻找最完美的视觉切分点。")

# ================= 第一阶段：导演思维分镜 =================
st.header("第一阶段：文案分镜拆解")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    # 【预处理】物理剥离原文本所有段落，防止AI参考原结构
    raw_content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    clean_stream = re.sub(r'[\s\n\r]+', '', raw_content).strip()
    st.session_state.original_text = clean_stream
    
    st.write(f"**文案流指纹已生成**（总计：{len(clean_stream)} 字）")

    if st.button("🚀 开始智能分镜处理"):
        if not api_key:
            st.error("请先输入 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 深度导演指令
                director_prompt = f"""你现在是一名资深电影剪辑师。你需要将以下一段【完全没有格式】的文案流进行无损分镜处理。

### 核心分镜准则：
1. **数字序号**：每一行必须以“数字.”开头，例如：1.文案内容
2. **拒绝平庸切割**：不要简单地每35个字一切。35个字是一个【时长预警线】，意味着视频生成上限是5秒。
3. **分镜技巧（节奏感）**：
   - **对话切换**：当换人说话时，必须另起分镜（即使那句话只有5个字）。
   - **场景/时间跳跃**：当故事地点改变或时间流转，必须另起分镜。
   - **语义聚拢（拒绝太碎）**：如果连续的短句属于同一场景下的连贯动作（如：他站起来，拿起杯子，喝了一口水），请聚拢在一个分镜中。
   - **长度平衡**：理想的分镜长度在 20-35 字符。如果一句话接近40字符，请观察是否有逻辑断点（如：逗号、转折词）进行拆分。
4. **无损原则**：严禁更改、删除、添加任何原文文字。你只是在文字间决定哪里该“剪一刀”。

### 待处理文案流：
{clean_stream}"""

                with st.spinner("导演正在构思分镜节奏..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你只输出分镜后的文案，不要有任何多余的开场白或解释。"},
                            {"role": "user", "content": director_instruction}
                        ],
                        temperature=0.3
                    )
                    st.session_state.storyboard_draft = response.choices[0].message.content
                    st.session_state.desc_batches = []
                    st.session_state.batch_progress = 0
            except Exception as e:
                st.error(f"处理报错: {str(e)}")

# 显示分镜结果与监控
if st.session_state.storyboard_draft:
    col_edit, col_monitor = st.columns([3, 2])
    
    with col_edit:
        st.subheader("✍️ 分镜精修区（可手动编辑）")
        edited_storyboard = st.text_area("分镜文案预览", value=st.session_state.storyboard_draft, height=500)
        st.session_state.storyboard_draft = edited_storyboard

    with col_monitor:
        st.subheader("📊 节奏监控面板")
        # 解析编辑框内容
        lines = [l.strip() for l in edited_storyboard.split('\n') if l.strip()]
        rebuilt_text = ""
        analysis_list = []
        
        for i, line in enumerate(lines):
            # 兼容各种序号格式并提取文案
            content = re.sub(r'^\d+[\.、\s]+', '', line)
            rebuilt_text += content
            char_len = len(content)
            
            # 节奏评价逻辑
            if char_len > 40: status = "🔴 太挤(超标)"
            elif char_len < 15: status = "🟡 略碎(视语义而定)"
            else: status = "🟢 理想"
            
            analysis_list.append({"序号": i+1, "字数": char_len, "节奏": status})
        
        # 无损校验
        if len(rebuilt_text) == len(st.session_state.original_text):
            st.success(f"✅ 文案无损：共 {len(rebuilt_text)} 字")
        else:
            diff = len(st.session_state.original_text) - len(rebuilt_text)
            st.error(f"⚠️ 内容偏差：差额 {diff} 字（请检查是否误删）")
            
        st.dataframe(pd.DataFrame(analysis_list), use_container_width=True)

    st.divider()

    # ================= 第二阶段：导演画面描述 =================
    st.header("第二阶段：AI画面与视频指令生成")
    
    char_desc = st.text_area("1. 录入核心角色视觉设定", 
                            placeholder="请描述角色外貌、衣着。例如：赵大帅：50岁，两撇胡须，身穿深蓝色军装，眼神威严。", 
                            height=100)
    
    if char_desc:
        # 获取最终分镜列表
        final_list = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in edited_storyboard.split('\n') if l.strip()]
        total_shots = len(final_list)
        idx = st.session_state.batch_progress
        batch_size = 20
        end_idx = min(idx + batch_size, total_shots)

        if idx < total_shots:
            if st.button(f"🎞️ 生成第 {idx+1} - {end_idx} 组画面描述"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_content = ""
                    for i, txt in enumerate(final_list[idx:end_idx]):
                        batch_content += f"分镜{idx+i+1}：{txt}\n"
                    
                    desc_prompt = f"""你现在是视觉导演，负责根据分镜文案生成画面提示词。

### 角色设定：
{char_desc}

### 任务要求：
1. **画面描述 (Midjourney)**：描述该镜头的静态视觉。必须包含：景别（如：特写、中景、远景）、人物的神态动作、环境细节、服装材质、光影氛围。**禁止描述动态演变**。
2. **视频生成 (即梦AI)**：描述这5秒内的【动态变化】。使用短句，描述人物的微表情演变、肢体位移、或者镜头的运动（如：拉近、摇移）。
3. **连贯性**：确保每个分镜中的人物外貌和场景元素高度统一，避免割裂。

### 待处理分镜：
{batch_content}"""

                    with st.spinner("AI正在深度构思视觉细节..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": desc_prompt}]
                        )
                        st.session_state.desc_batches.append(response.choices[0].message.content)
                        st.session_state.batch_progress = end_idx
                        st.rerun()
                except Exception as e:
                    st.error(f"描述生成失败: {e}")
        else:
            st.success("✅ 全部分镜描述已生成完毕")

        # 结果展示
        for b_idx, b_content in enumerate(st.session_state.desc_batches):
            with st.expander(f"📦 批次 {b_idx+1} 生成结果 (20组)", expanded=True):
                st.markdown(b_content)
