import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="AI分镜导演系统", layout="wide")

# --- 初始化 Session State ---
if 'editable_text' not in st.session_state:
    st.session_state.editable_text = "" # 存储AI生成的可编辑分镜文本
if 'final_batch_results' not in st.session_state:
    st.session_state.final_batch_results = [] # 存储第二步生成的描述
if 'batch_step' not in st.session_state:
    st.session_state.batch_step = 0

# --- 侧边栏 ---
st.sidebar.title("⚙️ 配置")
api_key = st.sidebar.text_input("API Key", type="password")
base_url = st.sidebar.text_input("中转地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.title("🎬 电影解说全流程分镜工具")

# ================= 第一阶段：智能分镜生成与人工校对 =================
st.header("Step 1: 剧情重组分镜 (可编辑)")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    # 彻底抹除原文段落
    scrubbed_text = raw_text.replace("\n", "").replace("\r", "").replace(" ", "").strip()
    
    if st.button("🪄 启动AI初步智能分镜"):
        if not api_key: st.error("请配置API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                # 强化“聚拢”逻辑：要求AI不要太碎
                seg_prompt = f"""你是一个资深电影导演。请将以下无段落文本重新进行分镜重组。
                
核心策略：
1. **语义聚拢**：严禁一句一分！将描述同一个动作流、同一个神态表情的连贯文字合并在同一个分镜中。
2. **字数控制**：每个分镜文案目标在 30-40 字符之间。只要总字数不超过40字，尽量将相关的动作“打包”。
3. **强制切分**：只有在角色切换、场景突变、或字数即将超过40字时，才开启新分镜。
4. **输出格式**：直接输出文案，每行代表一个分镜，序号开头。

文本：{scrubbed_text}"""
                
                with st.spinner("AI正在深度聚拢剧情..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": seg_prompt}]
                    )
                    # 将结果存入可编辑状态
                    st.session_state.editable_text = response.choices[0].message.content
            except Exception as e:
                st.error(f"失败: {e}")

# 展示编辑区与预览面板
if st.session_state.editable_text:
    col_edit, col_preview = st.columns([2, 1])
    
    with col_edit:
        st.subheader("✍️ 分镜编辑区 (你可以直接在此修改)")
        # 用户可以直接在文本框里增删，比如把两行合并成一行
        updated_text = st.text_area("分镜文案草稿", value=st.session_state.editable_text, height=400)
        st.session_state.editable_text = updated_text 
        
    with col_preview:
        st.subheader("📊 实时字数监控")
        # 解析编辑框里的每一行
        lines = [l.strip() for l in st.session_state.editable_text.split('\n') if l.strip()]
        analysis_data = []
        for i, line in enumerate(lines):
            # 提取文案内容（去掉前面的数字序号）
            clean_content = re.sub(r'^\d+[\.、\s]+', '', line)
            char_count = len(clean_content)
            
            if char_count > 40: status = "❌ 过长(超5s)"
            elif char_count < 20: status = "⚠️ 略短(建议合并)"
            else: status = "✅ 理想"
            
            analysis_data.append({"分镜": i+1, "字数": char_count, "状态": status})
        
        st.table(pd.DataFrame(analysis_data))

    st.divider()

    # ================= 第二阶段：根据最终确认的文案生成描述 =================
    st.header("Step 2: 生成 AI 画面与视频描述")
    
    char_info = st.text_area("输入核心人物设定", placeholder="例如：林凡：剑眉星目，黑色劲装...", height=100)
    
    if char_info:
        # 以用户最终编辑的 lines 为准
        final_lines = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in st.session_state.editable_text.split('\n') if l.strip()]
        total_shots = len(final_lines)
        curr = st.session_state.batch_step
        batch_size = 20
        end = min(curr + batch_size, total_shots)

        if curr < total_shots:
            if st.button(f"🚀 生成第 {curr + 1} - {end} 组深度描述"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_content = ""
                    for i, content in enumerate(final_lines[curr:end]):
                        batch_content += f"分镜{curr+i+1}：{content}\n"
                    
                    desc_prompt = f"""你现在是视觉导演。请为以下确定的分镜文案生成描述。
                    
角色设定：{char_info}

要求：
1. **画面描述 (MJ)**：静态视觉。包含：具体场景、人物着装细节、视角、光效。禁止描述动态行为。
2. **视频生成 (即梦AI)**：在图片基础上，描述这5秒内的动作。采用短句堆砌。遵循“单焦原则”，确保一个镜头只做一个核心动作流。
3. **连贯性**：由于现在的文案已经经过重组，每个分镜可能包含多个微动作，请在视频描述中完整体现文案所述的行为。

分镜组：
{batch_content}"""

                    with st.spinner("导演正在构思画面..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": desc_prompt}]
                        )
                        st.session_state.final_batch_results.append(response.choices[0].message.content)
                        st.session_state.batch_step = end
                        st.rerun()
                except Exception as e:
                    st.error(f"描述失败: {e}")
        else:
            st.success("✅ 全部描述已完成！")

        for idx, res in enumerate(st.session_state.final_batch_results):
            with st.expander(f"📦 批次 {idx+1} 详细提示词结果"):
                st.text_area(f"批次{idx+1}内容", res, height=400)
