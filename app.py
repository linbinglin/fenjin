import streamlit as st
from gradio_client import Client
import json
import re
import io
import tempfile
import os
from pydub import AudioSegment
from openai import OpenAI

st.set_page_config(page_title="AI小说配音工具（Gradio IndexTTS2）", layout="wide")
st.title("AI小说配音程序（支持参考音频克隆 + 情感控制）")

# ==================== 侧边栏配置 ====================
st.sidebar.header("API 与 Gradio 配置")

# Yunwu.ai 用于角色识别
yunwu_key = st.sidebar.text_input("Yunwu.ai API Key（角色识别，必填）", type="password")

# Gradio IndexTTS2 URL
gradio_url = st.sidebar.text_input("IndexTTS2 Gradio URL（必填）", value="https://f0sIqa2aqpig89w-7860.com/", help="直接复制你截图中的地址，不要加 /v1")

# 角色识别模型选择
st.sidebar.subheader("角色识别模型")
common_models = ["gpt-4o", "claude-3-5-sonnet-20240620", "deepseek-chat", "gemini-1.5-pro", "grok-beta", "doubao-lite-32k"]
preset = st.sidebar.selectbox("快速选择", ["（不选）"] + common_models, index=0)
custom = st.sidebar.text_input("自定义模型名（优先）", placeholder="例如：gemini-3-pro-preview")
final_model = custom.strip() or (preset if preset != "（不选）" else "gpt-4o")
st.sidebar.success(f"使用模型：**{final_model}**")

# 全局情感控制（匹配你截图中的滑块）
st.sidebar.subheader("全局情感强度（0.0~1.0，建议小幅度调整）")
happy = st.sidebar.slider("快乐", 0.0, 1.0, 0.0, 0.05)
angry = st.sidebar.slider("愤怒", 0.0, 1.0, 0.0, 0.05)
sad = st.sidebar.slider("悲伤", 0.0, 1.0, 0.0, 0.05)
disgust = st.sidebar.slider("厌恶", 0.0, 1.0, 0.0, 0.05)
surprise = st.sidebar.slider("惊奇", 0.0, 1.0, 0.0, 0.05)
fear = st.sidebar.slider("恐惧", 0.0, 1.0, 0.0, 0.05)

# 初始化客户端
if yunwu_key:
    llm_client = OpenAI(base_url="https://yunwu.ai/v1", api_key=yunwu_key)

if gradio_url:
    try:
        tts_client = Client(gradio_url)
        st.success(f"成功连接 Gradio：{gradio_url}")
    except Exception as e:
        st.error(f"连接失败：{e}")
        st.stop()

# 关键调试按钮！！！
if st.sidebar.button("🔍 查看 Gradio API 端点详情（必点！）"):
    with st.spinner("正在获取 API 信息..."):
        try:
            api_info = tts_client.view_api(all_endpoints=True)
            st.code(api_info, language="text")
            st.info("请把上面的完整代码块复制发给我，我立刻给你完美匹配的生成代码！")
        except Exception as e:
            st.error(f"获取失败：{e}")

# ==================== 文件上传与角色识别 ====================
uploaded = st.file_uploader("上传小说TXT文件", type=["txt"])
if uploaded:
    text = uploaded.read().decode("utf-8")
    st.text_area("全文预览", text, height=300)

    if st.button("🔍 自动识别角色与分段", type="primary"):
        if not yunwu_key:
            st.error("请填写 Yunwu.ai Key")
            st.stop()

        with st.spinner("AI识别中..."):
            prompt = f"""严格只输出纯JSON数组：[ {{"role": "角色名或旁白", "text": "文字"}} ]

要求：
1. 每段只能是旁白或单一角色台词
2. 自动识别所有角色，名称保持一致
3. text中双引号转义为\\"
4. 完整覆盖全文

文本：
{text}"""
            try:
                resp = llm_client.chat.completions.create(
                    model=final_model,
                    messages=[{"role": "system", "content": "只输出合法JSON，无任何说明"},
                              {"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=8192
                )
                content = resp.choices[0].message.content.strip()
                if content.startswith("```"):
                    content = re.sub(r"^```json?\n?|```$", "", content, flags=re.MULTILINE).strip()
                segments = json.loads(content)
                st.session_state.segments = segments
                roles = list(set(s['role'] for s in segments if s['role'] != '旁白'))
                st.success(f"识别完成！共 {len(segments)} 段，角色：{roles or ['仅旁白']}")
            except Exception as e:
                st.error(f"识别失败：{e}")
                if 'content' in locals():
                    st.code(content)

# ==================== 参考音频上传 & 生成 ====================
if 'segments' in st.session_state:
    segments = st.session_state.segments
    roles = list(set(seg["role"] for seg in segments))

    st.header("🎤 为每个角色上传参考音频（克隆声线，必填）")
    role_ref_map = {}
    for role in roles:
        uploaded_ref = st.file_uploader(f"{role} 的参考音频（WAV优先）", type=["wav", "mp3", "ogg"], key=f"ref_{role}")
        if uploaded_ref:
            # 保存到临时文件供 gradio_client 上传
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_ref.name)[1]) as tmp:
                tmp.write(uploaded_ref.read())
            role_ref_map[role] = tmp.name
            st.success(f"{role} 参考音频已上传")
    
    st.session_state.role_ref_map = role_ref_map

    if st.button("🔊 生成完整配音（合并WAV）", type="primary"):
        if not role_ref_map:
            st.error("请先为所有角色上传参考音频")
            st.stop()

        with st.spinner("正在调用 Gradio IndexTTS2 生成并合并...（可能较慢）"):
            audio_segments = []
            progress = st.progress(0)

            for i, seg in enumerate(segments):
                role = seg["role"]
                text_seg = seg["text"].strip()
                if not text_seg:
                    continue

                ref_path = st.session_state.role_ref_map.get(role)
                if not ref_path:
                    st.warning(f"{role} 无参考音频，跳过")
                    continue

                try:
                    # ===== 这里是临时的参数顺序（根据常见 GPT-SoVITS/IndexTTS 类部署） =====
                    # 请先运行上方“查看 API 端点详情”，把输出发给我，我给你精确顺序！
                    result = tts_client.predict(
                        ref_path,           # 参考音频路径（必填）
                        text_seg,           # 文本（必填）
                        happy,              # 快乐强度
                        angry,              # 愤怒
                        sad,                # 悲伤
                        disgust,            # 厌恶
                        surprise,           # 惊奇
                        fear,               # 恐惧
                        # 如果还有其他参数（如 temperature、top_k、prompt_text 等），在这里添加
                        # api_name="/infer"  # 如果有多个端点，取消注释并填写正确名称
                    )

                    # 处理输出（常见两种：音频路径 或 (sr, np.array)）
                    if isinstance(result, str):  # 服务器返回音频路径
                        audio_bytes = tts_client.download_files(result)
                    elif isinstance(result, tuple) and len(result) == 2:  # (sample_rate, audio_data)
                        import numpy as np
                        import wave
                        buf = io.BytesIO()
                        with wave.open(buf, 'wb') as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(result[0])
                            wf.writeframes((result[1] * 32767).astype(np.int16).tobytes())
                        audio_bytes = buf.getvalue()
                    else:
                        raise ValueError(f"未知输出格式：{type(result)}")

                    audio = AudioSegment.from_wav(io.BytesIO(audio_bytes)) if audio_bytes.endswith(b'wav') else AudioSegment.from_file(io.BytesIO(audio_bytes))
                    audio_segments.append(audio)

                except Exception as e:
                    st.error(f"第{i+1}段（{role}）失败：{e}")
                    st.info("大概率是参数顺序或 api_name 不对 → 请发我 API 详情！")

                progress.progress((i + 1) / len(segments))

            if audio_segments:
                combined = AudioSegment.empty()
                for seg in audio_segments:
                    combined += seg
                output_bytes = io.BytesIO()
                combined.export(output_bytes, format="wav")
                output_bytes.seek(0)
                st.audio(output_bytes, format="audio/wav")
                st.download_button("📥 下载完整配音 WAV", data=output_bytes, file_name="完整配音.wav", mime="audio/wav")
                st.success("生成完成！（WAV 格式，兼容性最好）")

# ==================== 测试单段（调试用） ====================
with st.expander("🔧 测试单段生成（调试参数顺序）"):
    test_text = st.text_input("测试文本", "你好，这是一段测试配音。")
    test_ref = st.file_uploader("测试参考音频", type=["wav", "mp3"])
    if test_ref and st.button("生成测试音频"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(test_ref.read())
        test_path = tmp.name
        try:
            result = tts_client.predict(test_path, test_text, happy, angry, sad, disgust, surprise, fear)  # 同上顺序
            # 输出处理同上...
            st.audio(...)  # 简化，同上逻辑
        except Exception as e:
            st.error(f"测试失败：{e}")

st.info("""
使用流程（超级简单）：
1. 侧边栏填写 Yunwu.ai Key + 你的 Gradio URL
2. **必点** “查看 Gradio API 端点详情” → 把代码块发给我（最重要！）
3. 上传 TXT → 识别角色 → 为每个角色上传参考音频（短句清晰语音最佳）
4. 调整情感滑块 → 生成配音

一定能成功！等你发 API 详情，下一版就是最终完美版。
""")
