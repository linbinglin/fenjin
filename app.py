import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# ==========================================
# 1. 核心工具函数：确保 1:1 像素级计算
# ==========================================

def get_pure_text(text):
    """提取纯净文案内容（不含编号）"""
    if not text: return ""
    # 彻底清除所有行首数字编号格式
    text = re.sub(r'^\s*\d+[\.、\s]\s*', '', text, flags=re.MULTILINE)
    # 彻底清除所有空白符
    return "".join(text.split())

def reindex_text(text):
    """一键强制重排序号"""
    lines = text.split('\n')
    valid_lines = []
    count = 1
    for line in lines:
        content = re.sub(r'^\s*\d+[\.、\s]\s*', '', line).strip()
        if content:
            valid_lines.append(f"{count}.{content}")
            count += 1
    return "\n".join(valid_lines)

# ==========================================
# 2. 页面配置与初始化
# ==========================================

st.set_page_config(page_title="全能分镜大师 V17", layout="wide")

if 'storyboard_output' not in st.session_state:
    st.session_state.storyboard_output = ""
if 'raw_clean_text' not in st.session_state:
    st.session_state.raw_clean_text = ""

with st.sidebar:
    st.title("⚙️ 系统引擎设置")
    api_key = st.text_input("1. API Key", type="password")
    base_url = st.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("3. Model ID", value="gpt-4o")
    
    st.divider()
    st.markdown("""
    **🎞️ 导演红线 (V17)：**
    - **单镜死线**：绝不准超 35 字。
    - **禁止脑补**：严禁重复、改写、增添。
    - **强制切分**：语义服从长度。
    """)

# ==========================================
# 3. 主界面逻辑
# ==========================================

st.title("🎬 电影解说·万能无损分镜系统 (V17)")
st.caption("针对长文案幻觉重复、分镜过长、字数偏差深度优化。")

file = st.file_uploader("📂 上传文案 TXT 文件", type=['txt'])

if file:
    raw_text = file.getvalue().decode("utf-8")
    # 锁定原始字符流
    st.session_state.raw_clean_text = "".join(raw_text.split())
    input_len = len(st.session_state.raw_clean_text)

    st.subheader("📊 文案逻辑校验看板")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 启动镜像级分镜处理"):
        if not api_key:
            st.error("请配置侧边栏参数")
        else:
            try:
                # 修复 URL 路径
                client = OpenAI(api_key=api_key, base_url=base_url.strip())
                
                # 物理切割：每 800 字一块，减小 AI 的认知负担，防止幻觉
                text_flow = st.session_state.raw_clean_text
                chunks = [text_flow[i:i+800] for i in range(0, len(text_flow), 800)]
                
                final_results = []
                idx_counter = 1
                bar = st.progress(0)
                
                for i, chunk in enumerate(chunks):
                    with st.spinner(f"正在镜像处理第 {i+1}/{len(chunks)} 段..."):
                        # V17 强制镜像指令：不准当导演，只准当切割机
                        system_prompt = f"""你是一个严格的文本切割机。
你的唯一任务是将用户输入的文本流，按顺序插入编号并换行。

【硬性要求】：
1. **绝对字数平衡**：每个分镜编号后的文字内容，必须在 20-35 个字之间。
2. **强制断句**：即便一句话没写完，只要字数接近 35 个字，必须立即截断开启新编号。
3. **零容忍脑补**：严禁增加、删减、润色、总结或重复原文任何字符。你输出的每一个字必须在原文中能找到 1:1 的对应。
4. **编号锚点**：从第 {idx_counter} 号开始。

【示例】：
1.我是名满京城的神秘画师一笔一
2.划皆能勾动男子情欲世间女子
（注意：为了死守字数，可以牺牲语义完整性）"""

                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": "你是一个没有感情的文本镜像切割机，只输出编号列表。"},
                                {"role": "user", "content": chunk}
                            ],
                            temperature=0
                        )
                        res_content = response.choices[0].message.content.strip()
                        final_results.append(res_content)
                        
                        # 更新下一段的序号
                        found_nums = re.findall(r'(\d+)[\.、]', res_content)
                        if found_nums:
                            idx_counter = int(found_nums[-1]) + 1
                        bar.progress((i+1)/len(chunks))

                st.session_state.storyboard_output = "\n".join(final_results)
                st.success("镜像分镜完成！")
            except Exception as e:
                st.error(f"处理失败：{str(e)}")

# ==========================================
# 4. 编辑与精密分析区
# ==========================================

if st.session_state.storyboard_output:
    st.divider()
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.subheader("📝 导演精修区")
        # 实时同步编辑器内容
        current_text = st.text_area(
            "手动调整内容（按回车增加分镜，删除合并）：",
            value=st.session_state.storyboard_output,
            height=600
        )
        
        c1, c2 = st.columns(2)
        if c1.button("🔢 校准并重排序号"):
            st.session_state.storyboard_output = reindex_text(current_text)
            st.rerun()
        
        c2.download_button("💾 下载全本分镜稿", st.session_state.storyboard_output, "final_storyboard.txt")

    with col_r:
        st.subheader("📊 节奏节奏实时监控")
        # 计算当前编辑器内的纯字数
        clean_output = get_pure_text(current_text)
        out_len = len(clean_output)
        diff = out_len - len(st.session_state.raw_clean_text)
        
        # 统计分镜行
        shot_lines = [l for l in current_text.split('\n') if re.match(r'^\d+', l.strip())]
        
        st.metric("生成分镜总数", f"{len(shot_lines)} 组")
        st.metric("当前还原字数", f"{out_len} 字")
        
        if diff == 0:
            st.success("✅ 字数 1:1 无损还原")
        else:
            st.error(f"❌ 偏差：{diff} 字")
            st.caption("正数表示 AI 脑补或重复了内容，负数表示漏字。")

        # 节奏表预览
        analysis = []
        for i, line in enumerate(shot_lines):
            txt = re.sub(r'^\d+[\.、\s]\s*', '', line)
            ln = len(txt)
            analysis.append({"镜": i+1, "字数": ln, "状态": "✅" if ln <= 35 else "❌太长"})
        
        st.dataframe(pd.DataFrame(analysis), height=400, use_container_width=True)
