import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="AI分镜导演Pro", layout="wide")

# --- 初始化状态 ---
if 'processed_text' not in st.session_state: st.session_state.processed_text = ""
if 'original_stream' not in st.session_state: st.session_state.original_stream = ""
if 'desc_results' not in st.session_state: st.session_state.desc_results = []
if 'current_batch' not in st.session_state: st.session_state.current_batch = 0

# --- 配置区 ---
st.sidebar.title("⚙️ 导演室配置")
api_key = st.sidebar.text_input("API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("模型选择", value="gpt-4o") # 建议使用强力模型

st.title("🎬 电影解说全流程分镜工具")
st.markdown("---")

# ================= 第一阶段：物理粉碎与无损重构 =================
st.header("Step 1: 文本去格式化与节奏重组")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    # 【核心操作】彻底物理删除原段落结构
    raw_content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    # 过滤掉所有换行、空格、制表符
    clean_stream = re.sub(r'[\s\n\r\t]+', '', raw_content).strip()
    st.session_state.original_stream = clean_stream
    
    st.info(f"已物理粉碎原段落。当前待处理字符流总长：{len(clean_stream)} 字。")

    if st.button("🚀 强制智能分镜（打破原文结构）"):
        if not api_key: st.error("请配置API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 针对“太碎”和“偷懒”定制的极端Prompt
                director_instruction = f"""你是一个顶级的电影剪辑导演。现在我给你一段完全没有段落的字符流，请你进行分镜切割。

### 你的核心分镜技巧：
1. **语义聚拢（防止太碎）**：一个分镜代表5秒视频。如果一句话很短（如“他走了过来”），严禁单独分镜！必须把它和后续的动作（如“坐在了沙发上，点燃了一根烟”）合并，只要总长不超过40字，尽量让分镜文案饱满，确保画面有动作跨度。
2. **硬性边界**：每个分镜文案严格限制在 30-40 字符。绝对禁止超过40个字符，否则视频时长不够。
3. **强制切分点**：只有在【角色变换对话】或【场景彻底改变】时，即使字数很少也必须切分。
4. **无损要求**：严禁修改、添加或删除任何字符。你只是在长句中插入换行符。

### 待处理字符流：
{clean_stream}"""

                with st.spinner("AI正在重新解构剧情节奏..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你只负责无损地在文本中插入换行符进行分镜，不准说任何废话。"},
                            {"role": "user", "content": director_instruction}
                        ],
                        temperature=0 # 降低随机性
                    )
                    st.session_state.processed_text = response.choices[0].message.content
                    st.session_state.desc_results = []
                    st.session_state.current_batch = 0
            except Exception as e:
                st.error(f"处理出错: {str(e)}")

# 展示与校验
if st.session_state.processed_text:
    col_edit, col_dash = st.columns([3, 2])
    
    with col_edit:
        st.subheader("✍️ 导演精修区")
        final_edit = st.text_area("分镜预览 (每行代表一个5秒分镜)", value=st.session_state.processed_text, height=450)
        st.session_state.processed_text = final_edit

    with col_dash:
        st.subheader("📈 字数与无损监控")
        lines = [l.strip() for l in final_edit.split('\n') if l.strip()]
        
        # 验证文本是否完整
        reconstructed = "".join([re.sub(r'^\d+[\.、\s]+', '', l) for l in lines])
        orig_len = len(st.session_state.original_stream)
        curr_len = len(reconstructed)
        
        if orig_len == curr_len:
            st.success(f"✅ 无损核对一致 (共{curr_len}字)")
        else:
            diff = orig_len - curr_len
            st.error(f"⚠️ 文本不匹配！原:{orig_len}字, 现:{curr_len}字 (差额:{diff})")

        # 分析每一行
        analysis = []
        for i, l in enumerate(lines):
            c = re.sub(r'^\d+[\.、\s]+', '', l)
            analysis.append({"分镜": i+1, "字数": len(c), "评估": "🟢 完美" if 25<=len(c)<=40 else "⚠️ 调整"})
        st.dataframe(pd.DataFrame(analysis), use_container_width=True)

    st.divider()

    # ================= 第二阶段：分步描述生成 =================
    st.header("Step 2: 生成画面描述与视频动态词")
    
    char_config = st.text_area("输入核心角色视觉设定", placeholder="例如：林凡：25岁，身穿黑色皮衣，眼神冷峻...")
    
    if char_config:
        clean_lines = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in lines]
        total_len = len(clean_lines)
        batch_idx = st.session_state.current_batch
        size = 20
        end_idx = min(batch_idx + size, total_len)

        if batch_idx < total_len:
            if st.button(f"🎨 生成批次描述 ({batch_idx+1}-{end_idx})"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_text = "\n".join([f"分镜{i+batch_idx+1}: {t}" for i, t in enumerate(clean_lines[batch_idx:end_idx])])
                    
                    desc_prompt = f"""你现在是视觉导演。请为以下分镜生成MJ提示词和即梦AI描述。

角色设定：{char_config}

任务：
1. **画面描述 (MJ)**：静态描述。场景、人物长相细节、着装、环境光影。严禁动作。
2. **视频生成 (即梦AI)**：动态描述。描述这5秒内人物的神态、微动作、镜头推移。
3. **分镜适配**：由于目前每个分镜文案较长（约30-40字），请在视频描述中通过“短句堆砌”展现出连续的动作感，不要只做一个动作。

分镜文案：
{batch_text}"""
                    
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": desc_prompt}]
                    )
                    st.session_state.desc_results.append(response.choices[0].message.content)
                    st.session_state.current_batch = end_idx
                    st.rerun()
                except Exception as e:
                    st.error(f"生成失败: {e}")
        
        for r in st.session_state.desc_results:
            st.markdown(r)
            st.divider()
