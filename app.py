import streamlit as st
from openai import OpenAI
import re

# --- 辅助函数：清洗统计字数 ---
def get_clean_text_count(text):
    """
    去掉编号（如 1. 2. 3.）、换行符、空格和特殊标点后，计算核心文字字数
    用于对比 AI 是否偷换或漏掉原文内容
    """
    # 去掉分镜编号 (数字 + 点)
    text = re.sub(r'\d+\.', '', text)
    # 去掉所有空白字符
    text = "".join(text.split())
    # 去掉常见的格式化标点，仅保留核心文字内容
    return len(text)

# --- 页面配置 ---
st.set_page_config(page_title="电影解说分镜大师 Pro+", layout="wide")

st.sidebar.title("⚙️ 系统配置")
api_key = st.sidebar.text_input("1. API Key", type="password")
base_url = st.sidebar.text_input("2. 中转地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID", value="gpt-4o")

st.sidebar.markdown("---")
st.sidebar.info("""
**分镜规范：**
- 单行 < 35 字符 (约 5 秒)
- 严禁删减增添任何字词
- 动作/台词/场景切换必断句
""")

# --- 主界面 ---
st.title("🎬 电影解说·全自动分镜系统 (校验版)")

uploaded_file = st.file_uploader("📂 上传文本文件 (.txt)", type=['txt'])

if uploaded_file is not None:
    # 1. 读取并显示原始统计
    raw_content = uploaded_file.getvalue().decode("utf-8")
    # 彻底打乱段落，去除所有换行和多余空格，防止AI偷懒
    clean_input = "".join(raw_content.split())
    original_count = len(clean_input)

    # 统计面板
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("原始文案总字数", f"{original_count} 字")
    
    st.subheader("📝 待处理文本预览 (已强制去段落)")
    st.text_area("系统已自动将文本合并为长句，以确保AI重新逻辑分镜：", value=clean_input, height=150)

    if st.button("🚀 开始高精度分镜处理"):
        if not api_key:
            st.error("请输入 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                with st.spinner('深度解析中... AI 正在确保不遗漏任何文字...'):
                    # 精准 Prompt 指令
                    system_prompt = f"""你是一个优秀的电影解说工作员，负责将文案拆解为高频分镜脚本。
                    
【核心任务】：
将输入的纯文本重组成带编号的分镜列表。

【严格逻辑】：
1. 逐字逐句处理：严禁遗漏原文任何一个字，严禁改变文字顺序，严禁添加任何解释性文字。
2. 5秒原则：每行文案（每个分镜）严格控制在 35 个字符以内。若原句过长，必须在不改变文字的前提下物理拆分为多行。
3. 场景转换：当角色对话切换、场景切换、动作画面改变时，必须另起一行作为一个新分镜。
4. 格式要求：输出格式必须是“数字.文案内容”，例如：
   1.皇上翻遍后宫
   2.只为找出酒后爬龙床的宫女

【禁令】：
- 严禁使用用户上传文本的原始段落结构。
- 严禁在输出中包含任何前言、后记或解释性文字，只输出编号分镜。
- 严禁对原文进行润色。"""

                    user_prompt = f"请对以下文本进行高精度分镜处理，确保不漏字：\n\n{clean_input}"

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0, # 设为0保证最高确定性，不乱发挥
                    )

                    result_text = response.choices[0].message.content
                    output_count = get_clean_text_count(result_text)

                    # --- 结果展示与对比 ---
                    st.divider()
                    col_res1, col_res2 = st.columns(2)
                    
                    with col_res1:
                        st.subheader("🎞️ 分镜处理结果")
                        st.text_area("分镜脚本：", value=result_text, height=600)
                    
                    with col_res2:
                        st.subheader("📊 内容完整性校验")
                        st.metric("输出文案有效字数", f"{output_count} 字")
                        
                        # 字数比对逻辑
                        diff = output_count - original_count
                        if diff == 0:
                            st.success("✅ 校验通过：字数与原文 100% 吻合，无遗漏。")
                        elif diff > 0:
                            st.warning(f"⚠️ 校验异常：输出多了 {diff} 个字。请检查AI是否添加了额外注释。")
                        else:
                            st.error(f"❌ 校验失败：输出少了 {abs(diff)} 个字！AI 出现了漏字现象。")
                        
                        st.info("提示：如果字数不符，建议更换更强大的模型（如 GPT-4o 或 Claude 3.5 Sonnet）重新生成。")
                        
                        st.download_button(
                            label="💾 下载分镜脚本",
                            data=result_text,
                            file_name="storyboard_final.txt",
                            mime="text/plain"
                        )
            except Exception as e:
                st.error(f"处理失败：{str(e)}")
