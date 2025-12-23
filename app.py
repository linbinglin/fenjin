import streamlit as st
from openai import OpenAI
import re

# --- 核心字数稽核函数 ---
def get_clean_text(text):
    # 移除所有分镜编号 (数字 + 点/顿号)
    text = re.sub(r'\d+[\.、]\s*', '', text)
    # 移除所有不可见字符、换行、空格
    return "".join(text.split())

# --- 页面配置 ---
st.set_page_config(page_title="电影解说分镜导演 Pro", layout="wide")

st.sidebar.title("🎬 导演工作台配置")
api_key = st.sidebar.text_input("API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("模型 ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.info("""
**🎞️ 导演分镜原则：**
1. **语义聚合**：短句必须合并，单行目标 25-35 字。
2. **拒绝碎镜头**：严禁把一个词拆成两行。
3. **视觉对齐**：一行文字 = 一个 4-5 秒的画面镜头。
4. **文字无损**：原文每个字都必须在结果中。
""")

# --- 主界面 ---
st.title("🎞️ 电影解说·智能语义分镜系统")
st.caption("解决分镜过碎、机械断句、漏字等核心痛点。")

uploaded_file = st.file_uploader("📂 上传解说文案 (.txt)", type=['txt'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    # 彻底打乱输入，让AI根据语义重新聚合
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    st.subheader("📊 文案数据稽核")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("待处理原文", f"{input_len} 字")

    if st.button("🚀 生成电影感分镜脚本"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                # 兼容不同中转站格式
                actual_base = base_url.split('/chat')[0]
                client = OpenAI(api_key=api_key, base_url=actual_base)
                
                with st.spinner('导演正在审片：聚合语义，优化节奏...'):
                    # --- 核心 Prompt 进化：引入语义聚合逻辑 ---
                    system_prompt = """你是一个经验丰富的电影解说导演。你的任务是把文案拆解为【电影感分镜】。
                    
【分镜聚合逻辑 - 核心】：
1. **拒绝碎片化**：严禁出现短于 15 字的分镜（除非是极强的悬念或惊悚瞬间）。如果连续几个短句的总长在 35 字以内，必须将它们合并在同一个编号内。
2. **长度平衡**：每个分镜（一行）的最理想长度是 25 到 35 个字符。
3. **断句准则**：
   - 严禁在词语、专有名词中间断开。
   - 必须以标点符号或自然的呼吸停顿点作为分镜切分点。
   - 如果一句话刚好 40 字，请寻找中间的逗号切分，而不是生硬地切断。
4. **零损失还原**：你是原文的搬运工。严禁删减、修改、润色原文任何字句！一个字都不能少！
5. **视觉单位**：每一个编号代表一个 5 秒左右的画面。请想象画面感，确保每行文字讲述了一个相对完整的画面动作。

【输出格式要求】：
1.文字内容
2.文字内容
（直接输出结果，不要任何前言，每行严禁超过 35 字）"""

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对这段文字流进行像素级还原分镜，注意合并短句，拒绝过碎：\n\n{input_stream}"}
                        ],
                        temperature=0, # 极低随机性保证不丢字
                    )

                    result = response.choices[0].message.content
                    output_stream = get_clean_text(result)
                    output_len = len(output_stream)
                    
                    lines = [l for l in result.split('\n') if l.strip() and re.match(r'^\d+', l.strip())]
                    count = len(lines)

                    # 更新看板
                    c2.metric("生成分镜数", f"{count} 组")
                    c3.metric("处理后字数", f"{output_len} 字")
                    diff = output_len - input_len
                    c4.metric("字数偏差", f"{diff} 字")

                    st.divider()

                    if diff == 0:
                        st.success("✅ 像素级还原成功：字数完全对齐，无漏字。")
                    else:
                        st.error(f"❌ 还原失败：字数偏差 {diff} 字。建议检查原文或更换更高端模型（如 GPT-4o）。")

                    res_c1, res_c2 = st.columns([2, 1])
                    with res_c1:
                        st.text_area("分镜脚本结果", value=result, height=600)
                    with res_c2:
                        st.info(f"💡 **导演分析：**\n当前平均每镜长度：{output_len/count:.1f} 字。\n最理想的解说节奏是每镜 28-33 字。")
                        st.download_button("💾 下载分镜稿", result, "storyboard.txt")

            except Exception as e:
                st.error(f"处理出错：{str(e)}")
