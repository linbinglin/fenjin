import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="AI电影解说分镜 Pro v5.0", layout="wide")

# --- 初始化全局状态 ---
if 'raw_stream' not in st.session_state: st.session_state.raw_stream = ""
if 'storyboard_draft' not in st.session_state: st.session_state.storyboard_draft = ""
if 'desc_results' not in st.session_state: st.session_state.desc_results = []
if 'process_batch' not in st.session_state: st.session_state.process_batch = 0

# --- 侧边栏设置 ---
st.sidebar.title("🎬 导演工作台配置")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID (如 grok-4.1, gpt-4o)", value="grok-4.1")

st.sidebar.markdown("""
### 🎥 分镜准则：
1. **聚拢语义**：严禁一句一分！25-35字为一个标准5秒镜头。
2. **动作连贯**：描述同一个角色的连贯动作必须放在一个分镜里。
3. **强制无损**：严禁修改、遗漏原文任何标点和文字。
""")

st.title("🎬 电影解说全流程分镜导演系统")
st.caption("版本：v5.0 | 专注解决分镜破碎与内容丢失问题")

# ================= 第一阶段：导演逻辑分镜 =================
st.header("Step 1: 文案解构与语义分镜")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    # 【物理粉碎】抹除所有原段落，让AI无法参考
    raw_content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    clean_stream = re.sub(r'[\s\n\r\t]+', '', raw_content).strip()
    st.session_state.raw_stream = clean_stream
    
    st.info(f"📋 **文案已无损粉碎**：原文总计 {len(clean_stream)} 字符。")

    if st.button("🚀 启动深度语义分镜"):
        if not api_key: st.error("请先输入 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 【重构版导演指令】
                director_prompt = f"""你是一名拥有15年经验的电影分镜导演。
现在的任务是把一段物理粉碎后的文案长龙，重新按照“电影叙事节奏”进行分镜切割。

### 核心分镜准则：
1. **拒绝破碎（关键）**：不要简单地一句一行。一个分镜对应的配音大约是5秒，字数目标是 25-35 个字。
2. **语义聚拢逻辑**：
   - 如果一句话只有10个字，必须观察后文。如果后文在描述同一个动作、同一个角色的状态，且合并后总字数在35字以内，【必须合并】。
   - 只有在【换人说话】、【场景转换】或【情节发生剧烈转折】时，即使字数不足25字也可以独立分镜。
3. **字数红线**：单行分镜严禁超过 38 字符，否则视频配音将溢出。
4. **无损要求**：严禁改动、总结、添加或删除任何原文中的文字和标点。
5. **格式规范**：每一行必须以“数字.”开头，例如：1.文案内容

待处理文案流：
{clean_stream}"""

                with st.spinner("导演正在进行语义建模与节奏切割..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你只输出带序号的分镜列表，不准有任何解释，不准丢字。"},
                            {"role": "user", "content": director_prompt}
                        ],
                        temperature=0.1 # 降低随机性
                    )
                    st.session_state.storyboard_draft = response.choices[0].message.content
                    st.session_state.desc_results = []
                    st.session_state.process_batch = 0
            except Exception as e:
                st.error(f"处理失败: {str(e)}")

# 展示监控面板
if st.session_state.storyboard_draft:
    # 实时解析数据
    lines = [l.strip() for l in st.session_state.storyboard_draft.split('\n') if l.strip()]
    rebuilt_text = "".join([re.sub(r'^\d+[\.、\s]+', '', l) for l in lines])
    
    # 统计看板
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文总字数", f"{len(st.session_state.raw_stream)} 字")
    c2.metric("分镜总数", f"{len(lines)} 组")
    c3.metric("还原后字数", f"{len(rebuilt_text)} 字")
    diff = len(st.session_stream) if 'session_stream' in locals() else len(st.session_state.raw_stream) - len(rebuilt_text)
    c4.metric("字数偏差", f"{len(rebuilt_text) - len(st.session_state.raw_stream)} 字", delta_color="inverse")

    if (len(rebuilt_text) - len(st.session_state.raw_stream)) != 0:
        st.error(f"❌ 丢字/多字警告！差额：{len(rebuilt_text) - len(st.session_state.raw_stream)} 字。请检查序号或内容是否被篡改。")

    col_edit, col_audit = st.columns([3, 2])
    with col_edit:
        st.subheader("✍️ 分镜编辑区")
        st.session_state.storyboard_draft = st.text_area("直接在此微调分镜（删除换行即合并，按回车即分镜）", 
                                                       value=st.session_state.storyboard_draft, height=500)
    with col_audit:
        st.subheader("📊 实时节奏分析")
        analysis_data = []
        for i, l in enumerate(lines):
            c = re.sub(r'^\d+[\.、\s]+', '', l)
            ln = len(c)
            # 状态评价
            if ln > 38: status = "🔴 太长(必断)"
            elif ln < 20: status = "🟡 偏短(建议合并)"
            else: status = "🟢 完美"
            analysis_data.append({"序号": i+1, "内容预览": c[:10]+"...", "长度": ln, "状态": status})
        st.dataframe(pd.DataFrame(analysis_data), use_container_width=True, height=450)

    st.divider()

    # ================= 第二阶段：深度导演提示词生成 =================
    st.header("Step 2: 生成 MJ 画面与即梦AI视频描述")
    char_preset = st.text_area("1. 录入本视频核心角色设定", 
                             placeholder="描述外貌、服装。例如：林凡：25岁，身穿黑色金纹劲装，腰间佩刀。", 
                             height=100)
    
    if char_preset:
        pure_lines = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in st.session_state.storyboard_draft.split('\n') if l.strip()]
        total = len(pure_lines)
        idx = st.session_state.process_batch
        size = 20
        end_idx = min(idx + size, total)

        if idx < total:
            if st.button(f"🎨 生成批次描述 ({idx + 1} - {end_idx})"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_text = "\n".join([f"分镜{i+idx+1}: {t}" for i, t in enumerate(pure_lines[idx:end_idx])])
                    
                    visual_prompt = f"""你现在是视觉导演，负责生成Midjourney生图和即梦AI运动指令。

角色预设：{char_preset}

任务要求：
1. **画面描述 (MJ)**：描述静态。包含景别（特写/全景）、人物精确外貌、服装细节、光影环境。禁止描述行为。
2. **视频生成 (即梦AI)**：描述5秒内的动作轨迹。基于文案，描述人物神态如何变化、肢体如何位移。使用“短句堆砌”。
3. **单焦原则**：每一个分镜重点突出一个视觉重心，确保画面逻辑丝滑。

分镜清单：
{batch_text}"""

                    with st.spinner("正在精修视觉细节..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": visual_prompt}]
                        )
                        st.session_state.desc_results.append(response.choices[0].message.content)
                        st.session_state.process_batch = end_idx
                        st.rerun()
                except Exception as e:
                    st.error(f"生成失败: {e}")
        else:
            st.success("🏁 全部分镜视觉描述已生成完成！")

        for r in st.session_state.desc_results:
            st.markdown(r)
            st.divider()
