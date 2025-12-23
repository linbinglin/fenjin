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
if 'final_descriptions' not in st.session_state:
    st.session_state.final_descriptions = []
if 'current_batch' not in st.session_state:
    st.session_state.current_batch = 0

# --- 侧边栏 ---
st.sidebar.title("🛠️ 导演配置中心")
api_key = st.sidebar.text_input("API Key", type="password")
base_url = st.sidebar.text_input("中转地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.title("🎬 电影解说无损分镜专家")
st.info("本系统采用【无损切割逻辑】，确保文案一字不差，同时适配 5 秒视频节奏。")

# ================= 第一阶段：无损分镜切割 =================
st.header("Step 1: 文本切割与节奏对齐")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    raw_content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    # 预处理：去掉所有换行，合并为纯字符流
    clean_raw = re.sub(r'\s+', '', raw_content)
    st.session_state.original_text = clean_raw
    
    if st.button("📽️ 启动智能无损分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                # 极其严厉的“无损”提示词
                system_prompt = f"""你是一个顶级的电影解说分镜导演。你的任务是进行【无损切割】。
                
【核心准则 - 违者重罚】：
1. 绝对严禁删除、添加、修改原文中的任何一个字。
2. 文本结构必须按照原文顺序。
3. 你的工作仅是在合适的逻辑点插入换行符。

【分镜切割逻辑】：
1. **长度硬指标**：每个分镜理想长度为30-38个字符。绝对不能超过40个字符（超过5秒）。
2. **逻辑切分点**：
   - 角色更换说话。
   - 场景发生地点改变。
   - 出现重大的、独立的动作动作（如：从“坐着”变成“站起”）。
3. **平衡感**：如果一段话只有10个字，但下一段话合并过来后总长仍小于38字，且动作连贯，请务必合并。不要分得太碎导致画面闪烁。

请处理以下文本：
{clean_raw}"""

                with st.spinner("AI正在进行精密切割..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "system", "content": system_prompt}],
                        temperature=0 # 强制要求确定性，不准自由发挥
                    )
                    st.session_state.editable_storyboard = response.choices[0].message.content
                    st.session_state.final_descriptions = []
                    st.session_state.current_batch = 0
            except Exception as e:
                st.error(f"处理失败: {e}")

# 预览与人工微调区
if st.session_state.editable_storyboard:
    col_edit, col_stat = st.columns([3, 2])
    
    with col_edit:
        st.subheader("📝 分镜编辑（实时同步）")
        edited_text = st.text_area("分镜文案", value=st.session_state.editable_storyboard, height=450, help="每行代表一个分镜。你可以手动合并或拆分。")
        st.session_state.editable_storyboard = edited_text

    with col_stat:
        st.subheader("📊 质量监控看板")
        # 数据解析
        lines = [l.strip() for l in edited_text.split('\n') if l.strip()]
        processed_lines = []
        full_recombined = ""
        
        for i, line in enumerate(lines):
            # 去掉序号
            content = re.sub(r'^\d+[\.、\s]+', '', line)
            full_recombined += content
            char_len = len(content)
            
            if char_len > 40: status = "🔴 太挤 (超5s)"
            elif char_len < 20: status = "🟡 太碎 (动作感弱)"
            else: status = "🟢 完美"
            
            processed_lines.append({"分镜": i+1, "文案预览": content[:15]+"...", "字数": char_len, "建议": status})
        
        # 核心：字数校验
        orig_len = len(st.session_state.original_text)
        new_len = len(full_recombined)
        
        if orig_len == new_len:
            st.success(f"✅ 无损检测通过：原文 {orig_len} 字 -> 分镜 {new_len} 字")
        else:
            diff = orig_len - new_len
            st.error(f"⚠️ 检测到丢字！原文 {orig_len} 字 -> 分镜 {new_len} 字 (少了 {diff} 字)")
            st.warning("提示：请检查是否有分镜被意外删除或合并。")
        
        st.dataframe(pd.DataFrame(processed_lines), use_container_width=True)

    st.divider()

    # ================= 第二阶段：分步描述生成 =================
    st.header("Step 2: 画面与视频逻辑生成")
    
    char_desc = st.text_area("输入角色视觉设定 (Midjourney生图关键)", placeholder="描述角色长相、穿着。例如：林凡：剑眉星目，黑色斗篷。")
    
    if char_desc:
        final_list = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in edited_text.split('\n') if l.strip()]
        total = len(final_list)
        idx = st.session_state.current_batch
        size = 20
        end = min(idx + size, total)

        if idx < total:
            if st.button(f"🎨 生成第 {idx+1} - {end} 组导演提示词"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_data = "\n".join([f"{i+idx+1}. {text}" for i, text in enumerate(final_list[idx:end])])
                    
                    prompt = f"""你现在是视觉导演。基于以下分镜文案和角色设定，生成MJ生图词和即梦AI动作词。

【角色设定】：{char_desc}

【要求】：
1. **画面描述 (MJ)**：仅描述静态。包含场景、人物特写细节、材质、光影。严禁动作词。
2. **视频生成 (即梦AI)**：描述5秒内的动作轨迹。针对当前分镜文案，描述人物神态变化、肢体位移。使用“短句堆砌”。
3. **单焦原则**：一个分镜专注一个核心视觉焦点。

【待处理分镜】：
{batch_data}"""

                    with st.spinner("导演正在精修描述..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        st.session_state.final_results.append(response.choices[0].message.content)
                        st.session_state.current_batch = end
                        st.rerun()
                except Exception as e:
                    st.error(f"描述生成失败: {e}")
        else:
            st.success("🏁 所有描述生成完毕！")

        for r_idx, r_text in enumerate(st.session_state.final_results):
            with st.expander(f"📦 批次 {r_idx+1} 生成结果"):
                st.text_area(f"Result {r_idx+1}", r_text, height=400)
