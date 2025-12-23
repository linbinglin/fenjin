import streamlit as st
from openai import OpenAI
import re

# --- 工具函数 ---
def get_pure_text(text):
    """提取分镜后的纯文本内容，用于字数校验"""
    # 移除数字编号（如 1. 10. 100.）
    text = re.sub(r'\d+[\.、]\s*', '', text)
    # 移除所有空白符和换行
    clean_text = "".join(text.split())
    return clean_text

# --- 页面配置 ---
st.set_page_config(page_title="解说分镜·像素级还原版", layout="wide")

st.sidebar.title("⚙️ 配置中心")
api_key = st.sidebar.text_input("API Key", type="password")
base_url = st.sidebar.text_input("API Base URL", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.warning("""
**💡 导演避雷指南：**
1. **单行限额**：严格禁止单行超过 35 字。
2. **禁止总结**：AI 必须像打字机一样还原原文。
3. **强制编号**：每行必须以 '数字.' 开头。
""")

# --- 主界面 ---
st.title("🎬 电影解说·像素级自动分镜系统")
st.caption("解决分镜太碎、漏字、超长等痛点。适用于所有文本类型。")

uploaded_file = st.file_uploader("📂 上传文本文件 (.txt)", type=['txt'])

if uploaded_file is not None:
    raw_content = uploaded_file.getvalue().decode("utf-8")
    # 清洗：合并所有行，去除原文可能存在的干扰格式
    input_clean = "".join(raw_content.split())
    input_len = len(input_clean)

    # 统计看板
    st.subheader("📊 文案状态监控")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("待处理总字数", f"{input_len} 字")

    if st.button("🔥 开始高精度分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                # 兼容性处理
                actual_url = base_url.split('/chat')[0]
                client = OpenAI(api_key=api_key, base_url=actual_url)
                
                with st.spinner('正在进行像素级拆解，请稍后...'):
                    # --- 终极 Prompt：像素级还原指令 ---
                    system_prompt = f"""你是一个电影解说脚本导演，你的工作是【无损拆解】文案。
                    
【核心红线】：
1. **零丢失还原**：严禁遗漏任何字！严禁合并、简化或改写原文内容！
2. **35字物理截断**：单个分镜（一行）绝对不能超过 35 个字符。如果原句很长，必须在逻辑处切断。
   - 错误：1.朕要找的人耳后有颗朱砂痣，你有吗，没等我求饶就被侍卫拖出去乱棍打死在宫墙下。（过长）
   - 正确：
     1.朕要找的人耳后有颗朱砂痣
     2.你有吗
     3.没等我求饶就被侍卫拖出去
     4.乱棍打死在宫墙下
3. **分镜逻辑**：
   - 同一个动作或短对话，只要总长不超过 35 字，尽量合并为一行以防止太碎。
   - 场景变迁、角色切换、大幅动作跨度必须换行。
4. **强制格式**：每行必须使用“数字.内容”的格式。
5. **任务流程**：将文本看作一个连续的字符流，每 20-35 个字符寻找一个语义点进行切分并编号。

不要输出任何前言和废话，直接输出分镜结果。"""

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请像素级拆解以下文本，确保不漏字，单行不超35字，必须带编号：\n\n{input_clean}"}
                        ],
                        temperature=0, # 锁定确定性
                    )

                    result_raw = response.choices[0].message.content
                    output_clean = get_pure_text(result_raw)
                    output_len = len(output_clean)
                    
                    # 分析分镜数
                    shot_lines = [l for l in result_raw.split('\n') if re.match(r'^\d+', l.strip())]
                    shot_count = len(shot_lines)

                    # 更新看板
                    m2.metric("生成分镜数", f"{shot_count} 组")
                    m3.metric("处理后字数", f"{output_len} 字")
                    diff = output_len - input_len
                    m4.metric("字数差值", f"{diff} 字", delta_color="inverse")

                    st.divider()

                    # 校验与展示
                    if diff != 0:
                        st.error(f"❌ 校验失败：当前误差 {diff} 字。AI 在处理时出现了漏字或擅自增词。")
                    else:
                        st.success("✅ 像素级校验通过：字数与原文完全一致。")

                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.text_area("分镜详情", value=result_raw, height=600)
                    with c2:
                        st.info("💡 **分镜优化策略：**\n如果分镜太碎，是 AI 还没掌握好 35 字的边界。如果字数对齐但太碎，说明语义点切分过频。")
                        st.download_button("💾 下载脚本", result_raw, file_name="storyboard.txt")

            except Exception as e:
                st.error(f"处理失败：{str(e)}")
