import streamlit as st
import json
from openai import OpenAI
import io
import os
import subprocess
import tempfile

st.set_page_config(page_title="AI小说配音工具", layout="wide")
st.title("AI小说配音程序（自部署云端IndexTTS2）")

# 侧边栏配置
st.sidebar.header("API 配置")

# Yunwu.ai 用于角色识别
yunwu_api_key = st.sidebar.text_input("Yunwu.ai API Key (用于角色识别)", type="password")
if not yunwu_api_key:
    st.sidebar.warning("请填写 Yunwu.ai Key 以启用角色识别")

# 自部署 IndexTTS2 配置
tts_base_url = st.sidebar.text_input(
    "IndexTTS2 API Base URL",
    value="https://ffo5lqa2aapiq89w-7860.containerx-gpu.com/",
    help="填写您的云端实例地址（包含末尾斜杠 / ）"
)
tts_api_key = st.sidebar.text_input("IndexTTS2 API Key (若无需认证可留空)", type="password", value="")
tts_model = st.sidebar.text_input("IndexTTS2 模型名称", value="indextts2", help="常见值：indextts2、IndexTTS-2、tts-1 等，若报错请尝试修改")

if not tts_base_url:
    st.warning("请在侧边栏输入您的 IndexTTS2 API Base URL")
    st.stop()

# LLM 客户端
if yunwu_api_key:
    llm_client = OpenAI(base_url="https://yunwu.ai/v1", api_key=yunwu_api_key)
else:
    llm_client = None

# TTS 客户端（自部署）
tts_client = OpenAI(base_url=tts_base_url.rstrip("/"), api_key=tts_api_key or "none")

# LLM 模型选择
llm_models = [
    "gpt-4o", "claude-3-5-sonnet-20240620", "deepseek-chat",
    "gemini-1.5-pro", "grok-beta", "doubao-lite-32k"
]
selected_llm = st.sidebar.selectbox("选择用于角色识别的AI模型", llm_models)

# 文件上传
uploaded_file = st.file_uploader("上传小说TXT文件（分镜内容）", type=["txt"])
if uploaded_file:
    text = uploaded_file.read().decode("utf-8")
    st.text_area("小说全文预览", text, height=300)

    # 自动识别角色
    if st.button("🔍 自动识别角色与分段", type="primary"):
        if not llm_client:
            st.error("请先填写 Yunwu.ai API Key")
            st.stop()

        with st.spinner("AI 正在分析文本，识别角色与台词..."):
            prompt = f"""你是一个专业的小说配音脚本分析师。请将以下小说文本分解为顺序的配音段落。

要求：
1. 每段只能是“旁白”（叙述文字）或某个角色的台词。
2. 自动识别所有出现的角色名。
3. 输出严格为JSON数组，格式：[ {{"role": "角色名或旁白", "text": "该段完整文字"}} ]
4. 覆盖全部文本，不添加任何解释或额外内容。

小说文本：
{text}
"""
            try:
                response = llm_client.chat.completions.create(
                    model=selected_llm,
                    messages=[
                        {"role": "system", "content": "你必须只输出纯JSON，不要任何说明。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4096
                )
                content = response.choices[0].message.content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
                segments = json.loads(content)
                st.session_state.segments = segments
                st.session_state.full_text = text
                unique_roles = list(set(s['role'] for s in segments if s['role'] != '旁白'))
                st.success(f"识别完成！共 {len(segments)} 段，检测到角色：{unique_roles}")
            except Exception as e:
                st.error(f"识别失败：{e}")

# 生成音频
if 'segments' in st.session_state:
    segments = st.session_state.segments

    st.header("🎤 当前设置：统一使用默认声线（后续可扩展克隆）")
    st.info("IndexTTS2 零样本克隆能力极强，后续可为每个角色上传参考音频实现不同声音")

    if st.button("🔊 生成完整配音", type="primary"):
        with st.spinner("正在调用您的云端IndexTTS2生成并合并音频..."):
            audio_bytes_list = []
            progress_bar = st.progress(0)
            for i, seg in enumerate(segments):
                text_seg = seg["text"].strip()
                if not text_seg:
                    continue
                try:
                    response = tts_client.audio.speech.create(
                        model=tts_model,
                        input=text_seg,
                        response_format="mp3"
                    )
                    audio_bytes_list.append(response.content)
                except Exception as e:
                    st.error(f"第 {i+1} 段（{seg['role']}）生成失败：{e}")
                progress_bar.progress((i + 1) / len(segments))

            if not audio_bytes_list:
                st.error("所有段落生成失败")
                st.stop()

            # 使用 ffmpeg 合并（不依赖 pydub）
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
                # 先尝试直接 copy（最快），失败则重新编码
                result = subprocess.run([
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
                    "-c", "copy", output_path
                ], capture_output=True)
                if result.returncode != 0:
                    st.warning("直接合并失败，自动切换为重新编码合并")
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

st.info("部署后若仍有问题，请截图最新错误。建议先用极短文本（1-2句）测试，确保TTS接口正常返回音频。")
