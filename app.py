import streamlit as st
from openai import OpenAI
import re

# ================= 页面配置 =================
st.set_page_config(
    page_title="AI 分镜分批生成器",
    page_icon="🎬",
    layout="wide"
)

# ================= Session State 初始化 (用于记忆状态) =================
if 'processed_result' not in st.session_state:
    st.session_state.processed_result = ""  # 存储已生成的最终结果
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0      # 当前处理到第几个分镜
if 'source_scenes' not in st.session_state:
    st.session_state.source_scenes = []     # 拆解后的源文案列表
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

# ================= 侧边栏设置 =================
with st.sidebar:
    st.title("⚙️ 参数设置")
    
    st.subheader("1. 接口配置")
    api_base = st.text_input(
        "Base URL", 
        value="https://blog.tuiwen.xyz/v1", 
        help="第三方中转地址，末尾通常需要/v1"
    )
    api_key = st.text_input("API Key", type="password")
    
    st.subheader("2. 模型选择")
    # 支持自定义模型ID，优先读取手动输入
    model_options = ["gpt-4o", "claude-3-5-sonnet-20240620", "deepseek-chat", "gemini-pro"]
    selected_model = st.selectbox("预设模型", model_options)
    custom_model = st.text_input("或手动输入 Model ID", placeholder="例如: gpt-4o-2024-08-06")
    final_model = custom_model if custom_model else selected_model
    
    st.divider()
    
    st.subheader("3. 批处理控制")
    batch_size = st.slider(
        "每次让AI处理几个分镜？", 
        min_value=1, 
        max_value=10, 
        value=3, 
        help="建议设为3-5个。数量越少，AI描述越详细，不易偷懒；数量越多，速度越快但容易简略。"
    )

    st.divider()
    st.subheader("4. 角色设定 (必须)")
    character_profile = st.text_area(
        "人物小传/外貌描写",
        height=200,
        placeholder="赵清月：清冷美人，一身白色刺绣绫罗纱衣...\n赵灵曦：明艳张扬，黄色妆花襦裙..."
    )

# ================= 核心函数 =================

def parse_source_text(text):
    """
    智能解析上传的文本，尝试按序号拆分为列表。
    支持格式：1. / 1、 / NO.1 / 1
    """
    # 统一换行符
    text = text.replace("\r\n", "\n")
    # 正则：匹配行首的数字加标点，例如 "1." "1、" "1 "
    # split 会保留分割符，我们需要重新拼接
    pattern = r'(^|\n)(\d+[.、:：\s])'
    segments = re.split(pattern, text)
    
    scenes = []
    current_scene = ""
    
    for segment in segments:
        if not segment: continue
        # 如果是数字开头（匹配结果），说明是新分镜的开始
        if re.match(r'\d+[.、:：\s]', segment):
             # 把之前的存入
            if current_scene.strip():
                scenes.append(current_scene.strip())
            current_scene = segment
        elif segment.strip() == "":
            continue # 跳过空行
        else:
            # 拼接内容
            current_scene += segment
            
    # 存入最后一个
    if current_scene.strip():
        scenes.append(current_scene.strip())
        
    # 如果正则解析失败（列表为空或只有1个），说明用户可能没标号，尝试按空行强行拆
    if len(scenes) < 2:
        scenes = [line.strip() for line in text.split('\n') if line.strip()]
        
    return scenes

def generate_prompt(batch_scenes, profile):
    """构建发送给AI的 Prompt"""
    scene_text = "\n\n".join(batch_scenes)
    
    return f"""
你是一个专业的分镜师。你需要处理以下【分镜文案片段】。
这是用户已经整理好的序号，但可能需要根据时长进一步拆分。

### 核心任务：
1. **分析文案时长**：视频生成限制每图5秒（约40字）。如果单条文案过长，请在保持原序号基础上拆分为 X-1, X-2。
2. **画面描述 (Midjourney)**：只描述静态场景、人物状态、构图、光影。必须包含【角色设定】中的外貌Tag。严禁大幅度动作描写。
3. **视频描述 (即梦AI)**：基于画面图，描述具体的人物动作、运镜、动态变化。
4. **严格格式**：请直接输出结果，不要废话。

### 角色设定（必须严格遵守外貌）：
{profile}

### 待处理的分镜文案：
{scene_text}

### 输出格式示例：
NO.1 文案：xxxx
画面描述：[场景]，[静态状态]，(角色名，外貌Tag...)
视频生成：[动作]，[运镜]
    """

# ================= 主界面逻辑 =================

st.title("🎬 AI 智能分镜 - 分批生成版")
st.markdown("上传已编号的分镜稿，**分批次**发送给AI，防止内容中断，保证每个镜头的描述质量。")

# 1. 文件上传
uploaded_file = st.file_uploader("📂 上传整理好的分镜 (.txt)", type=["txt"])

if uploaded_file:
    # 只有当文件改变时才重新解析
    file_content = uploaded_file.getvalue().decode("utf-8")
    
    # 如果还没有解析过，或者解析的内容为空，则执行解析
    if not st.session_state.source_scenes:
        st.session_state.source_scenes = parse_source_text(file_content)
        st.toast(f"✅ 成功解析出 {len(st.session_state.source_scenes)} 个分镜片段", icon="🎉")

    # 显示解析概况
    total_scenes = len(st.session_state.source_scenes)
    progress = st.session_state.current_index / total_scenes if total_scenes > 0 else 0
    
    st.write(f"📊 当前进度：**{st.session_state.current_index} / {total_scenes}**")
    st.progress(progress)

    # 2. 生成控制区
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # 判断是否全部完成
        if st.session_state.current_index < total_scenes:
            btn_label = "🚀 开始生成" if st.session_state.current_index == 0 else "⏭️ 继续生成下一批"
            if st.button(btn_label, type="primary"):
                if not api_key or not character_profile:
                    st.error("请先在左侧填写 API Key 和 角色设定！")
                else:
                    # 准备当前批次的数据
                    start_idx = st.session_state.current_index
                    end_idx = min(start_idx + batch_size, total_scenes)
                    current_batch = st.session_state.source_scenes[start_idx:end_idx]
                    
                    # 调用 AI
                    client = OpenAI(api_key=api_key, base_url=api_base)
                    
                    user_prompt = generate_prompt(current_batch, character_profile)
                    
                    st.session_state.is_processing = True
                    
                    try:
                        # 显示正在处理的内容
                        with st.spinner(f"正在分析第 {start_idx+1} 到 {end_idx} 个分镜..."):
                            response_container = st.empty()
                            full_response = ""
                            
                            stream = client.chat.completions.create(
                                model=final_model,
                                messages=[
                                    {"role": "system", "content": "你是一个严谨的AI分镜助手，严格按照用户要求输出格式。"},
                                    {"role": "user", "content": user_prompt}
                                ],
                                stream=True,
                                temperature=0.7
                            )
                            
                            # 流式输出当前批次结果
                            for chunk in stream:
                                if chunk.choices[0].delta.content:
                                    content = chunk.choices[0].delta.content
                                    full_response += content
                                    response_container.markdown(f"**当前批次预览：**\n\n{full_response}")
                            
                            # 追加到总结果中
                            st.session_state.processed_result += f"\n\n--- 批次 ({start_idx+1}-{end_idx}) ---\n\n" + full_response
                            
                            # 更新索引
                            st.session_state.current_index = end_idx
                            st.rerun() # 刷新页面更新进度条和按钮状态
                            
                    except Exception as e:
                        st.error(f"发生错误: {str(e)}")
        else:
            st.success("🎉 所有分镜已全部处理完毕！")
            if st.button("🔄 重置所有进度"):
                st.session_state.current_index = 0
                st.session_state.processed_result = ""
                st.rerun()

    # 3. 结果展示区
    st.divider()
    st.subheader("📝 最终完整结果")
    
    # 提供下载按钮
    st.download_button(
        label="💾 下载完整分镜描述 (.txt)",
        data=st.session_state.processed_result,
        file_name="ai_storyboard_output.txt",
        mime="text/plain"
    )
    
    # 显示文本框（只读）
    st.text_area(
        "结果预览（可手动编辑复制）", 
        value=st.session_state.processed_result, 
        height=600
    )

else:
    st.info("👈 请先在左侧上传文案文件")
