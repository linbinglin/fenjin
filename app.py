import streamlit as st
from openai import OpenAI
import re

# ================= 页面配置 =================
st.set_page_config(
    page_title="AI 分镜分批生成器 (强一致性版)",
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
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

# ================= 侧边栏设置 =================
with st.sidebar:
    st.title("⚙️ 设置")
    
    st.subheader("1. 接口配置")
    api_base = st.text_input("Base URL", value="https://blog.tuiwen.xyz/v1", help="末尾通常需要/v1")
    api_key = st.text_input("API Key", type="password")
    
    st.subheader("2. 模型选择")
    model_options = ["gpt-4o", "claude-3-5-sonnet-20240620", "deepseek-chat"]
    selected_model = st.selectbox("预设模型", model_options)
    custom_model = st.text_input("手动输入 Model ID (优先)", placeholder="例如: gpt-4o")
    final_model = custom_model if custom_model else selected_model
    
    st.divider()
    
    st.subheader("3. 批处理控制")
    batch_size = st.slider("每次处理分镜数", 1, 10, 3, help="建议3个，确保人设不丢失")

    st.divider()
    
    st.subheader("4. 角色设定 (⚠️必须填写)")
    st.info("请严格按格式：姓名：描述词")
    # 提供了默认值示范，强调格式的重要性
    default_profile = "赵清月：(清冷美人，眉眼极精致，肤白如雪，银丝蝴蝶坠珠簪，白色刺绣绫罗纱衣)\n赵灵曦：(明艳张扬，杏眼桃色腮，肤白如雪，金丝花纹簪，黄色妆花襦裙)"
    character_profile = st.text_area("人物小传/外貌描写", height=250, value=default_profile, placeholder=default_profile)

# ================= 核心逻辑修复区 =================

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
    if len(scenes) < 2: scenes = [line.strip() for line in text.split('\n') if line.strip()]
    return scenes

def generate_prompt(batch_scenes, profile):
    """
    【核心修复】：构建超强约束的 Prompt
    强制要求 AI 在输出画面描述时，必须【复制粘贴】用户提供的 profile
    """
    scene_text = "\n\n".join(batch_scenes)
    
    return f"""
你是一个严格执行命令的AI分镜师。你的任务是将文案转化为Midjourney（画面）和即梦AI（视频）的提示词。

### 🚨 最高优先级指令：人物一致性 🚨
你必须严格遵守以下【强制引用规则】：
1. 仔细阅读下方的【人物资料库】。
2. 在生成的每一个【画面描述】中，**只要该人物出现，你必须直接“复制粘贴”资料库中该人物括号内的所有外貌描述词**。
3. **禁止**自己编造衣服，**禁止**简化描述。如果文案没说换衣服，就必须用资料库里的默认着装。

【人物资料库 (必须死记硬背)】：
{profile}

---

### 任务要求：
1. **分镜拆分**：若单条文案超过40字或含多个动作，请拆分为 X-1, X-2。
2. **画面描述 (Midjourney)**：
   - 格式：场景环境，光影气氛，(人物A名字，**粘贴人物资料库里的外貌Tag**)，(人物B名字，**粘贴人物资料库里的外貌Tag**)
   - 注意：这是静态画面，不要写大幅度动作（如跑、跳），只写姿态（站立、侧身）。
3. **视频生成 (即梦AI)**：
   - 描述具体的动作变化、运镜方式。这是用来生成视频的，可以写大幅度动作。

### 待处理文案：
{scene_text}

### 请严格按以下格式输出（不要输出任何解释语）：

NO.x 文案：[文案内容]
画面描述：[场景]，[环境]，(角色名，粘贴对应的外貌描述...)
视频生成：[具体动作]，[运镜描述]
"""

# ================= 主界面逻辑 =================

st.title("🎬 AI 智能分镜 - 角色强一致性版")

uploaded_file = st.file_uploader("📂 上传分镜文案 (.txt)", type=["txt"])

if uploaded_file:
    file_content = uploaded_file.getvalue().decode("utf-8")
    
    if not st.session_state.source_scenes:
        st.session_state.source_scenes = parse_source_text(file_content)
        st.toast(f"已解析 {len(st.session_state.source_scenes)} 个分镜", icon="✅")

    total_scenes = len(st.session_state.source_scenes)
    progress = st.session_state.current_index / total_scenes if total_scenes > 0 else 0
    
    st.write(f"📊 进度：{st.session_state.current_index}/{total_scenes}")
    st.progress(progress)

    # 布局
    col1, col2 = st.columns([1, 3])
    
    with col1:
        # 检查是否全部完成
        if st.session_state.current_index < total_scenes:
            btn_text = "🚀 开始生成" if st.session_state.current_index == 0 else "⏭️ 继续生成下一批"
            
            if st.button(btn_text, type="primary"):
                # 检查必要条件
                if not api_key:
                    st.error("❌ 缺少 API Key")
                elif not character_profile.strip():
                    st.error("❌ 必须填写角色设定！否则画面无法统一。")
                else:
                    # 准备数据
                    start_idx = st.session_state.current_index
                    end_idx = min(start_idx + batch_size, total_scenes)
                    current_batch = st.session_state.source_scenes[start_idx:end_idx]
                    
                    # 生成 Prompt
                    user_prompt = generate_prompt(current_batch, character_profile)
                    
                    # 调用 API
                    client = OpenAI(api_key=api_key, base_url=api_base)
                    
                    try:
                        with st.spinner(f"正在严格按照人设生成第 {start_idx+1}-{end_idx} 个分镜..."):
                            response_box = st.empty()
                            full_text = ""
                            
                            stream = client.chat.completions.create(
                                model=final_model,
                                messages=[
                                    {"role": "system", "content": "你是一个没有感情的格式化机器。必须严格执行Prompt中的‘人物一致性’要求，必须原样复制人物外貌描述。"},
                                    {"role": "user", "content": user_prompt}
                                ],
                                stream=True,
                                temperature=0.6 # 稍微降低温度，让它更听话，减少胡编乱造
                            )
                            
                            for chunk in stream:
                                if chunk.choices[0].delta.content:
                                    content = chunk.choices[0].delta.content
                                    full_text += content
                                    response_box.markdown(f"**当前生成中...**\n\n{full_text}")
                            
                            # 存储结果
                            st.session_state.processed_result += f"\n\n{full_text}"
                            st.session_state.current_index = end_idx
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"API 错误: {str(e)}")
        else:
            st.success("🎉 全部完成！")
            if st.button("🔄 清空重置"):
                st.session_state.current_index = 0
                st.session_state.processed_result = ""
                st.rerun()

    # 结果显示区
    with col2:
        st.subheader("📝 生成结果区")
        if st.session_state.processed_result:
            st.download_button("💾 下载结果", st.session_state.processed_result, "分镜描述.txt")
            st.text_area("结果内容", st.session_state.processed_result, height=600)
        else:
            st.info("等待生成... 结果将显示在这里")
