import streamlit as st
from openai import OpenAI
import re
import httpx

# 页面配置
st.set_page_config(page_title="逻辑审计分镜助手", page_icon="⚖️", layout="wide")

st.title("⚖️ 逻辑审计分镜助手 (稳定版)")

# --- 侧边栏配置 ---
st.sidebar.header("⚙️ 配置中心")
api_key = st.sidebar.text_input("请输入 API Key", type="password")
raw_url = st.sidebar.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")

# 自动处理 URL 格式
base_url = raw_url.split("/chat/completions")[0] 

model_options = ["gpt-4o", "claude-3-5-sonnet-20240620", "deepseek-chat", "gemini-1.5-pro", "doubao-pro-128k"]
selected_model = st.sidebar.selectbox("选择模型 ID", model_options + ["手动输入"])
model_id = st.sidebar.text_input("自定义 Model ID", value="deepseek-chat") if selected_model == "手动输入" else selected_model

# --- 核心 Prompt ---
PROMPT_STAGE_1 = "你是一个电影导演。任务：请将以下连续文本拆分为逻辑分镜。标准：每当出现【新场景、新角色、新动作转折】时开启新分镜。严禁改动原文。格式：序号.内容"

PROMPT_STAGE_2 = """你是一个细节控【分镜逻辑审计师】。
第一遍分镜存在细节疏忽，请执行审计修正：
1. **长镜拆分**：检查字数超35字的分镜，即便没标点，只要中间有微小动作/角色变化，必须执行拆分。
2. **碎镜合并**：检查连续10字以内的碎镜，如同属一场景/动作且合并后不超35字，必须合并。
3. **文本溯源**：核对全文，确保不漏一个字，不少一个符号。
输出要求：仅输出“序号.内容”，禁止废话。"""

# --- 主界面 ---
uploaded_file = st.file_uploader("上传 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_content = uploaded_file.getvalue().decode("utf-8")
    cleaned_content = "".join(raw_content.split())
    
    col_in, col_s1, col_s2 = st.columns([1, 1, 1.2])
    with col_in:
        st.subheader("1. 原始文本")
        st.text_area("Original", cleaned_content, height=300)

    if st.button("🚀 开始双重审计"):
        if not api_key:
            st.error("❌ 请输入 API Key")
        else:
            # 使用带有超时的 http 客户端
            http_client = httpx.Client(timeout=100.0) # 设置 100 秒超时
            client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
            
            try:
                # --- 第一阶段 ---
                container1 = st.status("正在执行阶段一：逻辑初分...", expanded=True)
                with container1:
                    st.write("正在连接接口并发送请求...")
                    res1 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STAGE_1},
                            {"role": "user", "content": cleaned_content}
                        ],
                        temperature=0.3
                    )
                    stage1_out = res1.choices[0].message.content
                    st.write("✅ 阶段一完成！")
                    with col_s1:
                        st.subheader("2. 逻辑初稿")
                        st.text_area("Stage 1", stage1_out, height=400)

                # --- 第二阶段 ---
                container2 = st.status("正在执行阶段二：逻辑审计纠偏...", expanded=True)
                with container2:
                    st.write("正在比对原文进行合并与拆分手术...")
                    res2 = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": PROMPT_STAGE_2},
                            {"role": "user", "content": f"【原文】：{cleaned_content}\n\n【草稿】：{stage1_out}"}
                        ],
                        temperature=0.1
                    )
                    final_out = res2.choices[0].message.content
                    st.write("✅ 阶段二完成！")
                
                with col_s2:
                    st.subheader("3. 最终审计对齐版")
                    st.text_area("Final Output", final_out, height=400)
                    st.download_button("📥 下载结果", final_out, file_name="final_storyboard.txt")
                    st.success("处理成功！")

            except httpx.ReadTimeout:
                st.error("🚨 接口响应超时：由于双重分镜计算量大，中转接口没能在规定时间内返回结果，请检查网络或更换模型（如 DeepSeek 或 GPT-4o-mini 响应较快）。")
            except Exception as e:
                st.error(f"❌ 运行出错：{str(e)}")
                st.info("提示：请检查接口地址是否正确，或 Model ID 是否填写错误。")

st.markdown("---")
st.caption("提示：如果点击后没反应，请检查浏览器控制台或刷新页面重试。推荐使用响应极速的模型（如 DeepSeek V3）。")
