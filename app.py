import streamlit as st
from openai import OpenAI
import re
import pandas as pd

# ==========================================
# 1. 核心工具函数（像素级精确度）
# ==========================================

def get_pure_text(text):
    """提取纯净文案，不含编号，用于 1:1 核对"""
    if not text: return ""
    # 彻底清除行首所有可能的数字编号格式
    text = re.sub(r'^\s*\d+[\.、\s]\s*', '', text, flags=re.MULTILINE)
    return "".join(text.split())

def reindex_text(text):
    """手动调整后的一键序号重排"""
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
# 2. 页面设置
# ==========================================

st.set_page_config(page_title="无损分镜排字机 V18", layout="wide")

if 'story_data' not in st.session_state:
    st.session_state.story_data = ""
if 'raw_target' not in st.session_state:
    st.session_state.raw_target = ""

with st.sidebar:
    st.title("⚙️ 系统引擎设置")
    api_key = st.text_input("1. API Key", type="password")
    base_url = st.text_input("2. 接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("3. Model ID (重要)", value="gpt-4o")
    
    st.divider()
    st.error("**⚠️ 严正警告 (V18)：**")
    st.caption("1. 请确保 Model ID 填写正确（如 gpt-4o），不要填 grok-4.1。")
    st.caption("2. AI 此刻是排字机，严禁它修改任何文字内容。")

# ==========================================
# 3. 主界面逻辑
# ==========================================

st.title("🎬 电影解说·像素级无损分镜系统 (V18)")
st.caption("解决 AI 擅自改写内容、总结摘要、字数大幅偏差的问题。")

file = st.file_uploader("📂 上传文案 (.txt)", type=['txt'])

if file:
    raw_text = file.getvalue().decode("utf-8")
    # 锁定原始字符流，作为唯一真理
    st.session_state.raw_target = "".join(raw_text.split())
    input_len = len(st.session_state.raw_target)

    st.subheader("📊 实时逻辑校验")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("原文总字数", f"{input_len} 字")

    if st.button("🚀 启动无损分镜排版"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            try:
                # 规范化客户端
                client = OpenAI(api_key=api_key, base_url=base_url.strip())
                
                # 物理强切：每 600 字一段，减少 AI 脑补空间
                text_flow = st.session_state.raw_target
                chunks = [text_flow[i:i+600] for i in range(0, len(text_flow), 600)]
                
                final_output = []
                idx = 1
                progress = st.progress(0)
                
                for i, chunk in enumerate(chunks):
                    with st.spinner(f"正在排版第 {i+1}/{len(chunks)} 块..."):
                        # V18 机械指令：剥夺 AI 的创作权
                        system_prompt = f"""你是一个机械化的【文本排版员】。
你的任务是：将接收到的文本，原封不动地进行换行并加上编号。

【严禁触碰的红线】：
1. 禁止总结！禁止改写！禁止提取动作！禁止描述画面！
2. 必须保留原文的每一个字，严禁丢失任何文字内容。
3. 每个编号后的内容长度必须严格在 25 到 35 个汉字之间。
4. 只要达到 30 字左右，即便句子没写完，也必须立即换行并开启新编号。
5. 编号从 {idx} 开始递增。

【正确示例】：
输入：我是名满京城的神秘画师一笔一划皆能勾动男子情欲世间女子骂我伤风败俗可男人们却视若珍宝。
输出：
1.我是名满京城的神秘画师一笔一划皆
2.能勾动男子情欲世间女子骂我伤风
3.败俗可男人们却视若珍宝。"""

                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": "你不是作家，你是排版打字机。直接输出编号列表，严禁改词，严禁总结。"},
                                {"role": "user", "content": chunk}
                            ],
                            temperature=0
                        )
                        chunk_res = response.choices[0].message.content.strip()
                        final_output.append(chunk_res)
                        
                        # 获取最后的序号
                        nums = re.findall(r'(\d+)[\.、]', chunk_res)
                        if nums: idx = int(nums[-1]) + 1
                        progress.progress((i+1)/len(chunks))

                st.session_state.story_data = "\n".join(final_output)
                st.success("无损排版完成！")
            except Exception as e:
                st.error(f"引擎故障：{str(e)}")

# ==========================================
# 4. 精修与对账区
# ==========================================

if st.session_state.story_data:
    st.divider()
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.subheader("📝 导演精修编辑器")
        current_content = st.text_area(
            "手动调整（按回车增行，删除合并）：",
            value=st.session_state.story_data,
            height=600
        )
        
        c1, c2 = st.columns(2)
        if c1.button("🔢 一键校准所有序号"):
            st.session_state.story_data = reindex_text(current_content)
            st.rerun()
        
        c2.download_button("💾 下载最终分镜稿", st.session_state.story_data, "v18_output.txt")

    with col_r:
        st.subheader("📊 实时节奏分析")
        clean_res = get_pure_text(current_content)
        res_len = len(clean_res)
        diff = res_len - len(st.session_state.raw_target)
        
        shot_lines = [l for l in current_content.split('\n') if re.match(r'^\d+', l.strip())]
        
        st.metric("生成分镜总数", f"{len(shot_lines)} 组")
        st.metric("还原总字数", f"{res_len} 字")
        
        if diff == 0:
            st.success("✅ 像素级还原：0 偏差")
        else:
            st.error(f"❌ 字数偏差：{diff} 字")
            st.caption("AI 出现了删减或脑补，请根据编辑器微调。")

        # 节奏表预览
        analysis = []
        for i, line in enumerate(shot_lines):
            txt = re.sub(r'^\d+[\.、\s]\s*', '', line)
            ln = len(txt)
            analysis.append({"镜": i+1, "字数": ln, "状态": "✅" if ln <= 35 else "⚠️过长"})
        
        st.dataframe(pd.DataFrame(analysis), height=400, use_container_width=True)
