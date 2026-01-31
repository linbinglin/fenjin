import streamlit as st
import json
from openai import OpenAI
from pydub import AudioSegment
import io

st.set_page_config(page_title="AI小说配音工具", layout="wide")
st.title("AI小说配音程序（支持IndexTTS2云端配音）")

# 侧边栏配置
st.sidebar.header("API 与模型配置")
api_key = st.sidebar.text_input("Yunwu.ai API Key", type="password")
if not api_key:
    st.warning("请在侧边栏输入您的 Yunwu.ai API Key")
    st.stop()

client = OpenAI(base_url="https://yunwu.ai/v1", api_key=api_key)

# LLM 模型选择（包含您要求的所有模型，名称根据常见代理格式填写）
llm_models = [
    "gpt-4o",
    "claude-3-5-sonnet-20240620",
    "deepseek-chat",
    "gemini-1.5-pro",
    "grok-beta",
    "doubao-lite-32k",  # 豆包轻量版，可根据实际替换
]
selected_llm = st.sidebar.selectbox("选择用于角色识别的AI模型", llm_models)

# TTS 配置（固定使用 IndexTTS2，如需改为可选可取消注释）
tts_model = "indextts2"

# 预设声音选项（根据常见中文TTS预设，您可根据实际接口支持的声音名称调整）
voice_options = [
    "默认男声", "默认女声", "热情青年男", "温柔少女女",
    "成熟稳重男", "甜美可爱女", "旁白专用男声", "冷静叙述女声"
]

# 文件上传
uploaded_file = st.file_uploader("上传小说TXT文件（分镜内容）", type=["txt"])
if uploaded_file:
    text = uploaded_file.read().decode("utf-8")
    st.text_area("小说全文预览", text, height=300)

    # 自动识别角色
    if st.button("🔍 自动识别角色与分段", type="primary"):
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
                response = client.chat.completions.create(
                    model=selected_llm,
                    messages=[
                        {"role": "system", "content": "你必须只输出纯JSON，不要任何说明。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4096
                )
                content = response.choices[0].message.content.strip()
                # 清理可能的代码块
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                segments = json.loads(content)
                st.session_state.segments = segments
                st.session_state.full_text = text
                st.success(f"识别完成！共 {len(segments)} 段，检测到角色：{[s['role'] for s in segments if s['role'] != '旁白']}")
            except Exception as e:
                st.error(f"识别失败：{e}")
                st.code(content if 'content' in locals() else "无输出")

# 显示角色设置与生成音频
if 'segments' in st.session_state:
    segments = st.session_state.segments
    roles = list(set(seg["role"] for seg in segments))

    st.header("🎤 角色声音设置")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.write("**角色**")
    with col2:
        st.write("**分配声音**")

    voice_map = {}
    for role in roles:
        default_idx = 6 if role == "旁白" else 0
        with col1:
            st.write(role)
        with col2:
            voice_map[role] = st.selectbox(f"声音 - {role}", voice_options, index=default_idx, key=f"voice_{role}")

    st.session_state.voice_map = voice_map

    if st.button("🔊 生成完整配音", type="primary"):
        with st.spinner("正在调用云端IndexTTS2生成音频（可能需要几分钟）..."):
            audio_segments = []
            progress_bar = st.progress(0)
            for i, seg in enumerate(segments):
                role = seg["role"]
                text_seg = seg["text"].strip()
                if not text_seg:
                    continue
                voice = st.session_state.voice_map.get(role, voice_options[0])
                try:
                    # 调用云端 IndexTTS2（假设支持 OpenAI 风格的 audio/speech）
                    response = client.audio.speech.create(
                        model=tts_model,
                        voice=voice,          # 如果实际参数是 speaker/style 等，请修改
                        input=text_seg,
                        response_format="mp3"
                    )
                    audio_data = response.content
                    audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
                    audio_segments.append(audio)
                except Exception as e:
                    st.error(f"第 {i+1} 段（{role}）生成失败：{e}")
                progress_bar.progress((i + 1) / len(segments))

            if audio_segments:
                # 合并所有音频段
                combined = AudioSegment.empty()
                for seg in audio_segments:
                    combined += seg
                # 保存并提供预览/下载
                output_bytes = io.BytesIO()
                combined.export(output_bytes, format="mp3")
                output_bytes.seek(0)
                st.audio(output_bytes, format="audio/mp3")
                st.download_button(
                    label="📥 下载完整配音MP3",
                    data=output_bytes,
                    file_name="AI配音结果.mp3",
                    mime="audio/mp3"
                )
                st.success("配音生成完成！")
            else:
                st.error("所有段落生成失败，请检查API或声音参数")

st.info("提示：如果TTS声音参数与实际接口不符（如需使用speaker_id、emotion等），请修改 client.audio.speech.create 中的参数。")
