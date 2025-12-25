import streamlit as st
from openai import OpenAI
import re

# ================= 页面配置 =================
st.set_page_config(
    page_title="AI 分镜生产力工具 (MJ后缀修正版)",
    page_icon="🎬",
    layout="wide"
)

# ================= Session State 初始化 =================
if 'processed_result' not in st.session_state:
    st.session_state.processed_result = ""
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'source_scenes' not in st.session_state:
    st.session_state.source_scenes = []

# ================= 侧边栏设置 =================
with st.sidebar:
    st.title("⚙️ 工程设置")
    
    # 1. API 配置
    with st.expander("🔌 接口与模型 (必填)", expanded=True):
        api_base = st.text_input("Base URL", value="https://blog.tuiwen.xyz/v1")
        api_key = st.text_input("API Key", type="password")
        
        model_options = ["gpt-4o", "claude-3-5-sonnet-20240620", "deepseek-chat"]
        selected_model = st.selectbox("选择模型", model_options)
        custom_model = st.text_input("自定义 Model ID", placeholder="优先使用此ID")
        final_model = custom_model if custom_model else selected_model

    # 2. 画风控制 (修改点：明确只针对MJ)
    st.divider()
    st.subheader("🎨 MJ 画风控制")
    style_suffix = st.text_area(
        "画风后缀 (仅追加到画面描述)", 
        value="--ar 16:9 --v 6.0 --style raw",
        height=70,
        help="这些参数只会出现在【画面描述】的末尾。视频生成描述将保持纯净。"
    )

    # 3. 批处理策略
    st.divider()
    st.subheader("⚡ 批处理策略")
    batch_size = st.slider(
        "单次生成数量", 
        min_value=1, 
        max_value=50, 
        value=10, 
        help="推荐策略：先用10个测试，确认无误后拉到30个全速生成。"
    )

    # 4. 角色设定
    st.divider()
    st.subheader("👤 角色一致性")
    default_profile = "赵清月：(清冷美人，眉眼极精致，肤白如雪，银丝蝴蝶坠珠簪，白色刺绣绫罗纱衣)\n赵灵曦：(明艳张扬，杏眼桃色腮，肤白如雪，金丝花纹簪，黄色妆花襦裙)"
    character_profile = st.text_area("人物资料库 (括号Tag格式)", height=200, value=default_profile)

# ================= 核心逻辑 =================

def parse_source_text(text):
    """智能解析分镜序号"""
    text = text.replace("\r\n", "\n")
    pattern = r'(^|\n)(\d+[.、:：\s])'
    segments = re.split(pattern, text)
    scenes = []
    current_scene = ""
    for segment in segments:
        if not segment: continue
        if re.match(r'\d+[.、:：\s]', segment):
            if current_scene.strip(): scenes.append(current_scene.strip())
            current_scene = segment
        elif segment.strip() == "": continue
        else: current_scene += segment
    if current_scene.strip(): scenes.append(current_scene.strip())
    # 容错处理
    if len(scenes) < 2: 
        scenes = [line.strip() for line in text.split('\n') if line.strip()]
    return scenes

def generate_prompt(batch_scenes, profile, suffix):
    """
    【修改点】：构建 Prompt
    明确指示：后缀只加给画面，视频不要加
    """
    scene_text = "\n\n".join(batch_scenes)
    
    return f"""
你是一个专业分镜师。请处理以下分镜文案。

### 🚨 强制执行规则 🚨

1.  **人物一致性**：
    *   必须熟读下方的【人物资料库】。
    *   在【画面描述】中，只要出现该角色，必须**原样复制**括号内的外貌Tag。

2.  **后缀追加规则 (仅限画面)**：
    *   请将后缀 `{suffix}` 追加到每一个【画面描述】的末尾。
    *   **注意**：【视频生成】描述**严禁**添加此后缀。

3.  **分镜拆分与合并**：
    *   文案过长（>40字）或动作过多时，请拆分为 X-1, X-2。
    *   文案极短且画面连贯时，可合并。

4.  **描述分离**：
    *   **画面描述**：Midjourney用。静态，场景+人物状态+外貌Tag+后缀。
    *   **视频生成**：即梦AI用。动态，具体动作+运镜。(纯净描述，无参数)

---
【人物资料库】：
{profile}

【待处理文案】：
{scene_text}

---
### 输出格式（严格）：
NO.x 文案：[内容]
画面描述：[场景]，[静态动作]，(角色名，外貌Tag)，{suffix}
视频生成：[具体连贯动作]，[镜头运镜]
"""

# ================= 主界面 =================

st.title("🎬 AI 分镜生产力工具")
st.markdown("流程建议：1. 上传文案 -> 2. **先生成10个预览** -> 3. **调整滑块到30** -> 4. 继续生成剩余内容")

uploaded_file = st.file_uploader("📂 上传分镜文案 (.txt)", type=["txt"])

if uploaded_file:
    file_content = uploaded_file.getvalue().decode("utf-8")
    
    # 解析文件
    if not st.session_state.source_scenes:
        st.session_state.source_scenes = parse_source_text(file_content)
        st.toast(f"已识别 {len(st.session_state.source_scenes)} 个分镜片段", icon="✅")

    total_scenes = len(st.session_state.source_scenes)
    
    # 进度展示
    col_prog, col_stat = st.columns([3, 1])
    with col_prog:
        progress = st.session_state.current_index / total_scenes if total_scenes > 0 else 0
        st.progress(progress)
    with col_stat:
        st.caption(f"进度：{st.session_state.current_index} / {total_scenes}")

    # ================= 操作区 =================
    col1, col2 = st.columns([1, 4])
    
    with col1:
        # 动态按钮逻辑
        if st.session_state.current_index < total_scenes:
            # 计算本次将要处理的范围
            start_idx = st.session_state.current_index
            end_idx = min(start_idx + batch_size, total_scenes)
            count = end_idx - start_idx
            
            btn_label = "🚀 开始测试 (10个)" if start_idx == 0 else f"⏭️ 继续生成 ({count}个)"
            
            if st.button(btn_label, type="primary"):
                if not api_key:
                    st.error("请填写 API Key")
                elif not character_profile.strip():
                    st.error("请填写角色设定")
                else:
                    # 获取当前批次数据
                    current_batch = st.session_state.source_scenes[start_idx:end_idx]
                    
                    # 生成 Prompt (传入后缀)
                    user_prompt = generate_prompt(current_batch, character_profile, style_suffix)
                    
                    client = OpenAI(api_key=api_key, base_url=api_base)
                    
                    try:
                        with st.spinner(f"AI 正在推理第 {start_idx+1} - {end_idx} 个分镜..."):
                            response_placeholder = st.empty()
                            full_text = ""
                            
                            # 流式生成
                            stream = client.chat.completions.create(
                                model=final_model,
                                messages=[
                                    {"role": "system", "content": "你是一个严格执行格式的AI助手。"},
                                    {"role": "user", "content": user_prompt}
                                ],
                                stream=True,
                                temperature=0.6
                            )
                            
                            for chunk in stream:
                                if chunk.choices[0].delta.content:
                                    content = chunk.choices[0].delta.content
                                    full_text += content
                                    response_placeholder.markdown(f"**⚡ 正在生成...**\n\n{full_text}")
                            
                            # 完成后追加结果
                            header = f"\n\n=== 批次 {start_idx+1}-{end_idx} ===\n\n"
                            st.session_state.processed_result += (header + full_text)
                            st.session_state.current_index = end_idx
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"出错: {str(e)}")
        else:
            st.success("✅ 所有分镜处理完毕！")
            if st.button("🗑️ 清空重置"):
                st.session_state.current_index = 0
                st.session_state.processed_result = ""
                st.session_state.source_scenes = []
                st.rerun()

    # ================= 结果展示区 =================
    with col2:
        st.subheader("📝 结果输出")
        if st.session_state.processed_result:
            st.download_button(
                "💾 下载完整结果 (.txt)", 
                st.session_state.processed_result, 
                "分镜提示词_完整版.txt"
            )
            st.text_area(
                "结果预览", 
                value=st.session_state.processed_result, 
                height=600
            )
        else:
            st.info("👈 点击左侧按钮开始生成，结果将显示在这里。")
