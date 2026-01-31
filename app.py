import streamlit as st
import json
from openai import OpenAI
import io
import os
import subprocess
import tempfile
import re
import requests

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
    help="完整地址，包含 https 和末尾 /"
)
tts_api_key = st.sidebar.text_input("IndexTTS2 API Key (若无需认证可留空)", type="password", value="")
tts_model = st.sidebar.text_input("IndexTTS2 模型名称", value="indextts2", help="常见：indextts2、IndexTTS-2、tts-1")

# ==================== TTS Voice 参数（可选） ====================
st.sidebar.header("TTS Voice 参数（可选）")
st.sidebar.info("如果留空，将自动尝试无voice调用。先试本地软件成功的voice值")

common_voices = ["default", "male", "female", "zh_male", "zh_female", "Xiaoxiao", "Yunxi", "male_qn", "female_qn"]

selected_voice_preset = st.sidebar.selectbox("快速尝试常见voice", ["（留空）"] + common_voices, index=0)
custom_voice = st.sidebar.text_input(
    "voice 值（填写后优先使用，留空则自动降级）",
    value="" if selected_voice_preset == "（留空）" else selected_voice_preset,
    placeholder="例如：male / Xiaoxiao / 您本地成功的voice"
)

final_voice = custom_voice.strip() if custom_voice.strip() else None

if final_voice:
    st.sidebar.success(f"将优先使用 voice：**{final_voice}**")
else:
    st.sidebar.info("未填写 voice，将自动尝试无 voice 调用")

if not tts_base_url:
    st.warning("请填写 IndexTTS2 API Base URL")
    st.stop()

# LLM 客户端
if yunwu_api_key:
    llm_client = OpenAI(base_url="https://yunwu.ai/v1", api_key=yunwu_api_key)
else:
    llm_client = None

# TTS 客户端
tts_client = OpenAI(base_url=tts_base_url.rstrip("/"), api_key=tts_api_key or "none")

# ==================== API 连通性测试（关键调试工具） ====================
st.sidebar.header("调试工具")
if st.sidebar.button("🔗 测试 IndexTTS2 API 连通性"):
    with st.spinner("正在测试 API 是否可访问..."):
        test_url = tts_base_url.rstrip("/") + "/v1/models"
        headers = {}
        if tts_api_key:
            headers["Authorization"] = f"Bearer {tts_api_key}"
        try:
            resp = requests.get(test_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                models = resp.json()
                st.sidebar.success(f"连接成功！可用模型数：{len(models.get('data', []))}")
                st.sidebar.code(json.dumps(models, indent=2, ensure_ascii=False))
            else:
                st.sidebar.error(f"连接失败：HTTP {resp.status_code}\n{resp.text}")
        except Exception as e:
            st.sidebar.error(f"连接超时或错误：{e}")

# ==================== 角色识别模型选择 ====================
st.sidebar.header("角色识别模型设置")
common_models = ["gpt-4o", "claude-3-5-sonnet-20240620", "gemini-1.5-pro", "deepseek-chat"]
selected_preset = st.sidebar.selectbox("快速选择", ["（不选）"] + common_models, index=0)
custom_model = st.sidebar.text_input("模型名称（自主填写，以此为准）", value=selected_preset if selected_preset != "（不选）" else "")
final_model = custom_model.strip() or selected_preset
if not final_model:
    st.sidebar.error("必须填写模型名称")
    st.stop()
st.sidebar.success(f"使用模型：**{final_model}**")

# ==================== 文件上传与角色识别 ====================
uploaded_file = st.file_uploader("上传小说TXT文件", type=["txt"])
if uploaded_file:
    text = uploaded_file.read().decode("utf-8")
    st.text_area("全文预览", text, height=300)

    if st.button("🔍 自动识别角色与分段", type="primary"):
        if not llm_client:
            st.error("请填写 Yunwu.ai Key")
            st.stop()

        # （角色识别部分保持不变，已证明可正常工作）
        # ... [同之前代码的识别逻辑，省略以节省篇幅，您直接复制之前版本的识别部分即可]

# ==================== 生成音频（增强容错） ====================
if 'segments' in st.session_state:
    segments = st.session_state.segments

    st.header("🎤 配音设置")
    st.info("当前统一声线，后续可扩展多角色克隆")

    if st.button("🔊 生成完整配音", type="primary"):
        with st.spinner("正在生成配音..."):
            audio_bytes_list = []
            progress_bar = st.progress(0)
            for i, seg in enumerate(segments):
                text_seg = seg["text"].strip()
                if not text_seg:
                    continue

                success = False
                # 策略1：如果填写了voice，优先尝试带voice
                if final_voice:
                    try:
                        response = tts_client.audio.speech.create(
                            model=tts_model,
                            voice=final_voice,
                            input=text_seg,
                            response_format="mp3"
                        )
                        audio_bytes_list.append(response.content)
                        success = True
                    except Exception as e:
                        st.warning(f"第 {i+1} 段带 voice 调用失败：{e}")

                # 策略2：降级为无voice调用
                if not success:
                    try:
                        response = tts_client.audio.speech.create(
                            model=tts_model,
                            input=text_seg,
                            response_format="mp3"
                        )
                        audio_bytes_list.append(response.content)
                        success = True
                        st.info(f"第 {i+1} 段无 voice 调用成功")
                    except Exception as e:
                        st.error(f"第 {i+1} 段全部失败：{e}")

                progress_bar.progress((i + 1) / len(segments))

            if not audio_bytes_list:
                st.error("所有段落都失败！请先点击左侧“测试 API 连通性”检查连接")
                st.stop()

            # ffmpeg 合并（同之前）
            # ... [合并逻辑同之前]

            # 输出音频和下载
            # ... [同之前]

st.info("""
重要调试步骤：
1. 先点击左侧 “测试 IndexTTS2 API 连通性” 按钮！
   - 如果显示“连接失败”或超时 → 说明 Streamlit Cloud 无法访问您的实例（网络/防火墙问题）。
   - 解决办法：① 确保实例公网可访问 ② 或切换到 SiliconFlow 公共 API（我可以帮您改代码）。
2. 如果连接成功但配音仍失败 → 把具体错误截图发我。
""")
