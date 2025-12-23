import streamlit as st
from openai import OpenAI
import io
import pandas as pd

st.set_page_config(page_title="AI全流程分镜导演", layout="wide")

# 初始化 Session State
if 'segments' not in st.session_state:
    st.session_state.segments = []
if 'batch_index' not in st.session_state:
    st.session_state.batch_index = 0
if 'final_results' not in st.session_state:
    st.session_state.final_results = []

# 侧边栏 API 配置
st.sidebar.title("⚙️ 系统配置")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID (建议使用 Claude-3.5 或 GPT-4o)", value="gpt-4o")

st.sidebar.info("💡 提示：第一步分镜完成后，请核对预览面板中的字数是否均匀，确保动作连贯。")

st.title("🎬 电影解说全流程分镜导演系统")

# ================= 第一阶段：智能分镜拆解 =================
st.header("Step 1: 剧情拆解与分镜重组")
uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    raw_content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    # 彻底抹除原段落逻辑
    scrubbed_content = raw_content.replace("\n", "").replace("\r", "").replace(" ", "").strip()
    
    if st.button("🚀 开始智能分镜处理"):
        if not api_key:
            st.error("请先输入 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 增强的分镜 Prompt
                seg_prompt = f"""你是一个电影视觉导演。请将以下无段落文本重新进行分镜拆解。

你的核心任务：
1. **字数上限**：每一个分镜文案严格控制在 30-40 字符之间（为了匹配5秒音频）。
2. **动作聚合**：不要简单地一句一分。如果连续的句子在描述同一个角色的连贯动作或神态，且字数相加不超过40字，请将它们合并在一个分镜中。这样生成的视频才有动作跨度。
3. **强制分割**：若遇到场景切换、新角色开口说话、或者字数即将超标，必须立即切换到下一个分镜。
4. **原味保持**：严禁修改、添加或遗漏原文任何文字。

待处理文本：
{scrubbed_content}"""

                with st.spinner("正在进行深度剧情分析与分镜重组..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": seg_prompt}],
                        temperature=0.3 # 降低随机性，保证准确
                    )
                    raw_segments = response.choices[0].message.content.split('\n')
                    
                    # 过滤空行并清洗
                    processed_segments = []
                    for s in raw_segments:
                        s = s.strip()
                        if s and ('.' in s or '、' in s):
                            # 去掉 AI 可能自带的序号前缀，重新统一编号
                            content_only = s.split('.', 1)[-1].split('、', 1)[-1].strip()
                            processed_segments.append(content_only)
                    
                    st.session_state.segments = processed_segments
                    st.session_state.batch_index = 0
                    st.session_state.final_results = []
            except Exception as e:
                st.error(f"分镜异常: {str(e)}")

# 展示分镜预览面板 (带字数统计)
if st.session_state.segments:
    st.subheader("📊 分镜预览面板 (字数监控)")
    
    # 构造表格数据
    preview_data = []
    for i, seg in enumerate(st.session_state.segments):
        char_count = len(seg)
        # 根据字数给出建议
        status = "✅ 完美" if 25 <= char_count <= 40 else "⚠️ 偏短(建议合并)" if char_count < 25 else "❌ 过长(建议拆分)"
        preview_data.append({
            "分镜编号": i + 1,
            "文案内容": seg,
            "字数": char_count,
            "状态建议": status
        })
    
    df = pd.DataFrame(preview_data)
    st.table(df) # 使用表格展示，更直观

    st.divider()

    # ================= 第二阶段：分批描述生成 =================
    st.header("Step 2: 生成 AI 画面与视频描述")
    
    # 获取角色设定
    char_info = st.text_area("1. 请输入核心角色设定（着装、外貌）", 
                            placeholder="例如：\n林凡：剑眉星目，身穿黑色金纹劲装，腰间佩刀。",
                            height=100)
    
    if char_info:
        total = len(st.session_state.segments)
        current = st.session_state.batch_index
        end = min(current + 20, total)
        
        if current < total:
            if st.button(f"🎬 生成第 {current + 1} - {end} 组描述"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_list = st.session_state.segments[current:end]
                    
                    # 构建带上下文的描述 Prompt
                    batch_content = ""
                    for i, text in enumerate(batch_list):
                        batch_content += f"分镜{current + i + 1}：{text}\n"
                        
                    desc_prompt = f"""你现在是视觉导演，负责根据分镜文案，设计Midjourney生图提示词和即梦AI视频运动提示词。

角色设定：
{char_info}

要求：
1. **画面描述 (MJ)**：描述分镜中的静态视觉。包含：具体场景、人物的外貌、精细的着装细节、视角（特写/全景）、光效。**禁止出现动作词**。
2. **视频生成 (即梦AI)**：在图片基础上，描述这5秒内发生的动作流。采用**短句堆砌**。描述人物的神态变化、肢体位移、镜头推进方式。遵循“单焦原则”，确保动作连贯有故事感。
3. **一致性**：必须严格遵守角色设定中的外貌描述，确保每个分镜的人不走样。

待处理分镜组：
{batch_content}"""

                    with st.spinner(f"正在深度解析第 {current+1} 批次描述..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": desc_prompt}],
                            temperature=0.7
                        )
                        st.session_state.final_results.append(response.choices[0].message.content)
                        st.session_state.batch_index = end
                        st.rerun()
                except Exception as e:
                    st.error(f"描述生成失败: {str(e)}")
        else:
            st.success("✨ 所有分镜描述已全部生成！")

        # 结果分批展示
        for idx, result in enumerate(st.session_state.final_results):
            with st.expander(f"📦 第 {idx+1} 批次生成结果 (20组)", expanded=True):
                st.text_area(f"批次{idx+1}结果", result, height=500)
