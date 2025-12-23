import streamlit as st
from openai import OpenAI
import re

# --- 核心字数稽核函数 ---
def get_pure_text(text):
    """提取纯文本内容，排除编号和空白字符"""
    # 移除数字编号（如 1. 或 123.）
    text = re.sub(r'\d+[\.、]\s*', '', text)
    # 移除所有不可见字符、换行、空格
    return "".join(text.split())

# --- 页面配置 ---
st.set_page_config(page_title="电影解说分镜导演 Pro V3", layout="wide")

# --- 侧边栏配置 ---
st.sidebar.title("⚙️ 导演工作台")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID (重点)", value="gpt-4o", help="请填入正确的模型名，如 gpt-4o 或 deepseek-chat")

st.sidebar.divider()
st.sidebar.markdown("""
**🎞️ 分镜聚合逻辑：**
1. **聚合优先**：单行目标字数 28-35 字，拒绝短碎。
2. **像素还原**：严禁漏字，漏字即报错。
3. **视觉切换**：仅在对话切换、大动作、场景变换时强断。
""")

# --- 主界面 ---
st.title("🎞️ 电影解说·智能语义分镜系统")
st.caption("当前版本：解决分镜过碎（900+）、漏字（-43）、机械断句问题。")

uploaded_file = st.file_uploader("📂 选择本地 TXT 文案", type=['txt'])

if uploaded_file is not None:
    # 读取文案并打乱段落，强制去格式化
    raw_text = uploaded_file.getvalue().decode("utf-8")
    input_stream = "".join(raw_text.split())
    input_len = len(input_stream)

    # 监控面板
    st.subheader("📊 文案稽核面板")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 生成电影感分镜脚本"):
        if not api_key:
            st.error("请先在左侧输入 API Key")
        elif "grol" in model_id:
            st.error(f"Model ID 错误：找不到模型 '{model_id}'。请尝试输入 'gpt-4o'。")
        else:
            try:
                # 自动修正 Base URL 格式
                api_url = base_url.split('/chat')[0].strip()
                client = OpenAI(api_key=api_key, base_url=api_url)
                
                with st.spinner('正在进行语义聚合与分镜规划...'):
                    # --- 终极聚合指令 ---
                    system_prompt = """你是一个顶级的解说导演。你的目标是把文案拆解为适合 5 秒画面的分镜（25-35字）。

【核心指令 - 拒绝碎片化】：
1. **聚合优先**：严禁无意义的短句换行。如果几句连续的话总字数在 35 字以内，必须合并在同一个编号里。
2. **像素级还原**：你是一个字都不能少的搬运工。严禁删减、总结、改写或润色原文。输出字数必须与输入完全相等。
3. **断句边界**：
   - 每行上限 35 字。
   - 必须在标点符号处切分，严禁在词语中间生硬切断。
   - 仅在以下情况允许切分：单行字数即将超过 35 字、更换对话角色、发生剧烈动作变化。
4. **编号要求**：每行必须以“数字.”开头，例如：
   1.皇上翻遍后宫，只为找出酒后爬龙床的宫女。
   2.第一世，我冒名承认，以为能一步登天。

【拒绝事项】：
- 拒绝 900 组那种机械拆分。
- 拒绝任何前言或解释。"""

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文字流进行像素级还原分镜，确保单行接近35字，不漏字：\n\n{input_stream}"}
                        ],
                        temperature=0, # 保证稳定性
                    )

                    result = response.choices[0].message.content
                    output_stream = get_pure_text(result)
                    output_len = len(output_stream)
                    
                    # 统计行数
                    shot_lines = [l for l in result.split('\n') if re.match(r'^\d+', l.strip())]
                    count = len(shot_lines)

                    # 更新监控
                    c2.metric("生成分镜数", f"{count} 组")
                    c3.metric("处理后字数", f"{output_len} 字")
                    diff = output_len - input_len
                    c4.metric("字数偏差", f"{diff} 字")

                    st.divider()

                    if diff == 0:
                        st.success("✅ 像素级对齐成功！文字 100% 还原。")
                    else:
                        st.error(f"❌ 字数不匹配！偏差：{diff} 字。AI 出现了删减或增添。")

                    res_c1, res_c2 = st.columns([2, 1])
                    with res_c1:
                        st.text_area("分镜脚本预览", value=result, height=600)
                    with res_c2:
                        st.info(f"💡 **分析报告：**\n当前分镜数从 900+ 压缩至 {count} 组。\n平均每镜承载：{output_len/count:.1f} 字。\n这属于完美的解说节奏（每镜停留约4.5秒）。")
                        st.download_button("💾 下载分镜稿", result, "script.txt")

            except Exception as e:
                st.error(f"处理出错：{str(e)}")
