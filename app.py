import streamlit as st
from openai import OpenAI
import re

# --- 工具函数 ---
def count_pure_text(text):
    # 移除编号和空白符计算纯文字
    text = re.sub(r'\d+\.', '', text)
    clean_text = "".join(text.split())
    return len(clean_text)

def analyze_scenes(text):
    # 计算分镜总数和平均字数
    lines = [line for line in text.split('\n') if line.strip() and re.match(r'^\d+\.', line.strip())]
    scene_count = len(lines)
    total_chars = count_pure_text(text)
    avg_chars = total_chars / scene_count if scene_count > 0 else 0
    return scene_count, avg_chars

# --- 页面配置 ---
st.set_page_config(page_title="解说分镜 Pro 2.0", layout="wide")

st.sidebar.title("⚙️ 高级配置")
api_key = st.sidebar.text_input("API Key", type="password")
base_url = st.sidebar.text_input("中转地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.sidebar.divider()
st.sidebar.markdown("""
**💡 优化后的分镜逻辑：**
1. **合并叙述**：同一人连续说话或同一连贯动作，合并输出。
2. **长度平衡**：尽量让每行接近 25-35 字。
3. **拒绝碎片**：严禁出现 10 字以下的无意义拆分。
""")

# --- 主界面 ---
st.title("🎬 电影解说·智能分镜系统 (防碎片版)")

uploaded_file = st.file_uploader("📂 上传文案 (.txt)", type=['txt'])

if uploaded_file is not None:
    raw_content = uploaded_file.getvalue().decode("utf-8")
    merged_input = "".join(raw_content.split()) # 强力去段落
    input_count = len(merged_input)

    # 统计面板
    st.subheader("📊 文案数据监控")
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    stat_col1.metric("原文总字数", f"{input_count} 字")

    if st.button("🚀 智能重构分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                # 兼容中转接口
                clean_url = base_url.replace("/chat/completions", "").replace("/chat/completion", "")
                client = OpenAI(api_key=api_key, base_url=clean_url)
                
                with st.spinner('正在进行语义聚合，优化分镜节奏...'):
                    # --- 核心指令：引入语义聚合逻辑 ---
                    system_prompt = """你是一个资深的电影解说导演。你需要将文案重组成高质量的分镜脚本。
                    
【分镜聚合原则 - 拒绝碎片化】：
1. **语义合并**：如果一句话很短，且后续动作或台词属于同一情境，必须合并在一起。不要每一小句都换行。
2. **字数饱和度**：每个分镜的目标长度是 20 到 35 个字符。只有当字数超过 35 字，或者发生了剧烈的场景/角色切换时，才允许分行。
3. **切换触发点**：
   - A 说话结束，换成 B 说话。
   - 环境从 室内 切换到 室外，或时间大幅跳跃。
   - 一个核心动作完成（如：从“跪地求饶”转变为“皇帝起身离去”）。
4. **文字精度**：严禁删减或增加原文中的任何字句。
5. **拒绝碎片**：禁止出现诸如“1.他走了”“2.回头了”这种碎片，应合并为“1.他走了之后又再次回头”。

【输出格式】：
1.文案内容
2.文案内容
（严禁输出任何多余的开场白或解释）"""

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"请对以下文案进行语义聚合分镜处理，保持35字限制但拒绝碎片化：\n\n{merged_input}"}
                        ],
                        temperature=0,
                    )

                    result_text = response.choices[0].message.content
                    output_count = count_pure_text(result_text)
                    scene_num, avg_len = analyze_scenes(result_text)

                    # 更新统计面板
                    stat_col2.metric("生成分镜数", f"{scene_num} 组")
                    stat_col3.metric("平均每镜字数", f"{avg_len:.1f} 字")
                    
                    diff = output_count - input_count
                    stat_col4.metric("字数偏差", f"{diff} 字")

                    # 结果区
                    st.divider()
                    if diff != 0:
                        st.error(f"⚠️ 字数校验未通过！漏字或多字：{diff} 字")
                    else:
                        st.success("✅ 字数完整性校验通过")

                    res_col1, res_col2 = st.columns([2, 1])
                    with res_col1:
                        st.text_area("分镜结果预览", value=result_text, height=600)
                    with res_col2:
                        st.info("💡 导演建议：\n当前平均字数控制在25字以上为佳。如果分镜依然过多，建议调高聚合度。")
                        st.download_button("💾 下载脚本", result_text, "script.txt")

            except Exception as e:
                st.error(f"处理失败：{str(e)}")
