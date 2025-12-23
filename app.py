import streamlit as st
from openai import OpenAI
import io

st.set_page_config(page_title="电影解说AI全流程分镜师", layout="wide")

# --- 侧边栏配置 ---
st.sidebar.title("⚙️ 配置中心")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.sidebar.markdown("""
### 📘 创作规范
1. **40字原则**：文案超40字自动拆分，确保视频时长够用。
2. **MJ描述**：静态场景+人物外貌+着装（不含动作）。
3. **即梦描述**：镜头语言+核心动作（短句化，单焦原则）。
4. **一致性**：强制带入预设的角色外貌描述。
""")

# --- 主界面 ---
st.title("🎬 电影解说全流程分镜助手")
st.caption("从文案到分镜，从Midjourney画面到即梦AI视频运动描述")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. 故事文案 (TXT)")
    text_file = st.file_uploader("上传文案文件", type=['txt'])
    
with col2:
    st.subheader("2. 核心角色外貌设定")
    character_info = st.text_area(
        "描述每个角色的外貌、穿着（用于保持画面一致性）", 
        placeholder="例如：\n赵清月：清冷美人，银丝蝴蝶簪，白色刺绣绫罗纱衣。\n赵灵曦：明艳张扬，杏眼桃腮，黄色妆花襦裙。",
        height=150
    )

if text_file and character_info:
    raw_text = io.StringIO(text_file.getvalue().decode("utf-8")).read()
    
    if st.button("🚀 生成深度分镜指令"):
        if not api_key:
            st.error("请输入API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                system_prompt = f"""你是一个顶级的电影解说导演和AI视频专家。
你的任务是根据提供的【文案】和【角色设定】，生成完美适配Midjourney（生图）和即梦AI（生视频）的分镜脚本。

### 核心约束：
1. **分镜切分**：每个分镜对应的文案严禁超过40个字符（约5秒音频）。超过则必须拆分为多个分镜。
2. **场景切换/对话切换**：必须作为新分镜。
3. **角色一致性**：必须在每个分镜的【画面描述】中包含提供的【角色设定】。

### 描述生成逻辑（即梦AI适配）：
- **画面描述 (Midjourney)**：描述场景、环境、人物静态外表、着装、光影。**禁止描述动作**。
- **视频生成 (即梦AI)**：描述动作、表情、镜头语言。采用**短句堆砌**。
- **单焦原则**：一个视频分镜只强调1-2个动作，避免三方复杂互动。

### 角色设定参考：
{character_info}

### 输出格式（严格遵守）：
数字序号.【文案内容】
- 画面描述：[场景 + 人物外表着装 + 艺术风格]
- 视频生成：[镜头动作 + 人物神态动作 + 氛围]
--------------------------------------------------
"""

                with st.spinner("导演正在构思画面，请稍后..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文案进行二次分镜和画面导演描述：\n\n{raw_text}"}
                        ],
                        temperature=0.7,
                        stream=True
                    )
                    
                    st.subheader("📽️ 最终导演分镜表")
                    placeholder = st.empty()
                    full_response = ""
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            placeholder.markdown(full_response)
                            
                    st.download_button("导出分镜脚本", full_response, file_name="director_script.txt")

            except Exception as e:
                st.error(f"处理失败: {str(e)}")
