import streamlit as st
import json
from openai import OpenAI
import io
import os
import subprocess
import tempfile
import re

st.set_page_config(page_title="AI小说配音工具", layout="wide")
st.title("AI小说配音程序（自部署云端IndexTTS2）")

# ==================== 侧边栏配置 ====================
st.sidebar.header("API 配置")

yunwu_api_key = st.sidebar.text_input("Yunwu.ai API Key (用于角色识别)", type="password")
if not yunwu_api_key:
    st.sidebar.warning("请填写 Yunwu.ai Key 以启用角色识别")

tts_base_url = st.sidebar.text_input(
    "IndexTTS2 API Base URL",
    value="https://ffo5lqa2aapiq89w-7860.containerx-gpu.com/",
    help="填写您的云端实例地址（包含末尾斜杠 / ）"
)
tts_api_key = st.sidebar.text_input("IndexTTS2 API Key (若无需认证可留空)", type="password", value="")
tts_model = st.sidebar.text_input("IndexTTS2 模型名称", value="indextts2", help="常见值：indextts2、IndexTTS-2 等")

if not tts_base_url:
    st.warning("请在侧边栏输入您的 IndexTTS2 API Base URL")
    st.stop()

if yunwu_api_key:
    llm_client = OpenAI(base_url="https://yunwu.ai/v1", api_key=yunwu_api_key)
else:
    llm_client = None

# ==================== TTS Voice 参数设置（关键修复） ====================
st.sidebar.header("TTS Voice 参数设置（必须填写）")
st.sidebar.info("您的实例要求 voice 参数，请填写本地软件能成功的 voice 值")

common_voices = [
    "default", "male", "female",
    "zh_male", "zh_female",
    "Xiaoxiao", "Yunxi", "Yunjian",
    "male_qn", "female_qn"
]

selected_voice_preset = st.sidebar.selectbox("① 快速尝试常见voice", ["（不选）"] + common_voices, index=0)

custom_voice = st.sidebar.text_input(
    "② voice 参数（自主填写，以此为准）",
    value=selected_voice_preset if selected_voice_preset != "（不选）" else "",
    placeholder="例如：default / male / Xiaoxiao / 您本地软件成功的voice"
)

final_voice = custom_voice.strip()
if not final_voice and selected_voice_preset != "（不选）":
    final_voice = selected_voice_preset

if not final_voice:
    st.sidebar.error("必须选择或填写 voice 参数！")
    st.stop()

st.sidebar.success(f"当前使用 voice：**{final_voice}**")

# ==================== 角色识别模型选择 ====================
st.sidebar.header("角色识别模型设置")
st.sidebar.info("推荐稳定模型：gpt-4o、claude-3-5-sonnet-20240620、gemini-1.5-pro")

common_models = [
    "gpt-4o", "gpt-4o-mini",
    "claude-3-5-sonnet-20240620", "claude-3-5-sonnet-20241022",
    "deepseek-chat", "gemini-1.5-pro", "gemini-1.5-flash",
    "grok-beta", "doubao-lite-32k"
]

selected_preset = st.sidebar.selectbox("① 快速选择常用模型", ["（不选）"] + common_models, index=0)
custom_model = st.sidebar.text_input(
    "② 模型名称（自主填写，以此为准）",
    value=selected_preset if selected_preset != "（不选）" else "",
    placeholder="例如：gpt-4o"
)

final_model = custom_model.strip()
if not final_model and selected_preset != "（不选）":
    final_model = selected_preset

if not final_model:
    st.sidebar.error("必须选择或填写一个模型名称")
    st.stop()

st.sidebar.success(f"当前使用模型：**{final_model}**")

# ==================== 文件上传与角色识别 ====================
uploaded_file = st.file_uploader("上传小说TXT文件（分镜内容）", type=["txt"])
if uploaded_file:
    text = uploaded_file.read().decode("utf-8")
    st.text_area("小说全文预览", text, height=300)

    if st.button("🔍 自动识别角色与分段", type="primary"):
        if not llm_client:
            st.error("请先填写 Yunwu.ai API Key")
            st.stop()

        with st.spinner("AI 正在分析文本，识别角色与台词..."):
            prompt = f"""你是一个专业的小说配音脚本分析师。请将以下小说文本分解为顺序的配音段落。

要求：
1. 每段只能是“旁白”（叙述文字）或某个角色的台词。
2. 自动识别所有出现的角色名（保持一致）。
3. 输出严格为完整的JSON数组，格式：[ {{"role": "角色名或旁白", "text": "该段完整文字"}} ]
4. text字段中的双引号必须转义为 \\"
5. 覆盖全部文本，绝不能截断。
6. 只输出纯JSON。

小说文本：
{text}
"""

            try:
                response = llm_client.chat.completions.create(
                    model=final_model,
                    messages=[
                        {"role": "system", "content": "你必须只输出完整的合法JSON数组。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=8192
                )
                content = response.choices[0].message.content.strip()

                if content.startswith("```"):
                    content = content.split("```")[1].strip()
                    if content.lower().startswith("json"):
                        content = content[4:].strip()

                try:
                    segments = json.loads(content)
                except json.JSONDecodeError as e:
                    st.warning(f"JSON解析失败，尝试修复：{e}")
                    content = re.sub(r',\s*]', ']', content)
                    content = content.strip()
                    if not content.endswith(']'): content += ']'
                    if not content.startswith('['): content = '[' + content
                    try:
                        segments = json.loads(content)
                        st.info("自动修复成功")
                    except:
                        st.error("修复失败")
                        st.code(content)
                        st.stop()

                st.session_state.segments = segments
                unique_roles = list(set(s['role'] for s in segments if s['role'] != '旁白'))
                st.success(f"识别完成！共 {len(segments)} 段，检测到角色：{unique_roles}")

            except Exception as e:
                st.error(f"识别失败：{e}")

# ==================== 生成音频 ====================
if 'segments' in st.session_state:
    segments = st.session_state.segments
    tts_client = OpenAI(base_url=tts_base_url.rstrip("/"), api_key=tts_api_key or "none")

    st.header("🎤 当前设置：统一使用同一voice（所有角色+旁白）")
    st.info("IndexTTS2 支持声线克隆，后续可为每个角色上传参考音频实现不同声音")

    if st.button("🔊 生成完整配音", type="primary"):
        with st.spinner("正在调用云端IndexTTS2生成并合并音频..."):
            audio_bytes_list = []
            progress_bar = st.progress(0)
            for i, seg in enumerate(segments):
                text_seg = seg["text"].strip()
                if not text_seg:
                    continue
                try:
                    response = tts_client.audio.speech.create(
                        model=tts_model,
                        voice=final_voice,  # 关键：添加voice参数
                        input=text_seg,
                        response_format="mp3"
                    )
                    audio_bytes_list.append(response.content)
                except Exception as e:
                    st.error(f"第 {i+1} 段（{seg['role']}）生成失败：{e}")
                progress_bar.progress((i + 1) / len(segments))

            if not audio_bytes_list:
                st.error("所有段落生成失败，请检查 voice 参数是否正确")
                st.stop()

            # ffmpeg 合并
            with tempfile.TemporaryDirectory() as tmpdir:
                input_paths = []
                for idx, audio_bytes in enumerate(audio_bytes_list):
                    path = os.path.join(tmpdir, f"seg{idx}.mp3")
                    with open(path, "wb") as f:
                        f.write(audio_bytes)
                    input_paths.append(path)

                list_path = os.path.join(tmpdir, "list.txt")
                with open(list_path, "w") as f:
                    for p in input_paths:
                        f.write(f"file '{p}'\n")

                output_path = os.path.join(tmpdir, "output.mp3")
                result = subprocess.run([
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                    "-c", "copy", output_path
                ], capture_output=True)
                if result.returncode != 0:
                    subprocess.run([
                        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                        "-c:a", "libmp3lame", output_path
                    ], check=True)

                with open(output_path, "rb") as f:
                    combined_bytes = f.read()

            output_io = io.BytesIO(combined_bytes)
            st.audio(output_io, format="audio/mp3")
            st.download_button(
                label="📥 下载完整配音MP3",
                data=output_io,
                file_name="AI配音_IndexTTS2.mp3",
                mime="audio/mp3"
            )
            st.success("配音生成并合并完成！")

st.info("""
部署要求：
- requirements.txt：streamlit\nopenai
- packages.txt：ffmpeg
建议：先用极短文本（1-2句）测试配音，找到正确的 voice 值后再处理长文。
如果还有报错（比如 voice 不支持），请把错误截图发我，我继续帮您调。
""")
