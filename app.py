import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="电影解说AI分镜导演", layout="wide")

# --- 初始化 Session State ---
if 'original_raw' not in st.session_state: st.session_state.original_raw = ""
if 'current_storyboard' not in st.session_state: st.session_state.current_storyboard = ""
if 'batch_results' not in st.session_state: st.session_state.batch_results = []
if 'process_idx' not in st.session_state: st.session_state.process_idx = 0

# --- 侧边栏配置 ---
st.sidebar.title("⚙️ 导演室设置")
api_key = st.sidebar.text_input("API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.title("🎬 电影解说全流程无损分镜导演")
st.info("💡 核心规则：35字/5秒原则，一字不差，强制序号。")

# ================= 第一阶段：物理粉碎与分镜重组 =================
st.header("Step 1: 文案重组分镜 (无损切割)")

uploaded_file = st.file_uploader("选择本地TXT文案", type=['txt'])

if uploaded_file:
    # 彻底抹除原段落逻辑
    raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    # 物理粉碎：去掉所有换行、空格、特殊制表符
    clean_stream = re.sub(r'[\s\n\r\t]+', '', raw_text).strip()
    st.session_state.original_raw = clean_stream
    
    st.write(f"✅ **文本已物理粉碎**：待处理字符总数 {len(clean_stream)} 字。")

    if st.button("🚀 开始生成分镜草稿"):
        if not api_key:
            st.error("请先配置 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 极端严厉的 Step 1 指令
                step1_prompt = f"""你是一个电影分镜导演。你的任务是对下面这段没有任何段落的文案进行【无损分镜切割】。

### 强制准则（必须严格遵守）：
1. **绝对无损**：严禁删除、修改、缩减、添加原文中的任何一个字。
2. **强制序号**：每一行必须以“数字.”开头，例如：1.文案内容
3. **字数红线**：每个分镜文案理想在 20-35 字符。绝对禁止超过 40 字符（对应5秒音频）。
4. **分镜逻辑**：
   - 只要遇到：角色说话、场景切换、核心动作改变，必须另起一行作为新分镜。
   - 如果连续短句在35字内且属于同一连贯动作，请聚拢在一行。

### 待处理字符流：
{clean_stream}"""

                with st.spinner("AI 正在逐字分析并进行无损分镜..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你是一个无损分镜机器人。只输出带序号的分镜，不准说废话，不准漏字。"},
                            {"role": "user", "content": step1_prompt}
                        ],
                        temperature=0 # 强制确定性
                    )
                    st.session_state.current_storyboard = response.choices[0].message.content
                    st.session_state.batch_results = []
                    st.session_state.process_idx = 0
            except Exception as e:
                st.error(f"分镜生成异常: {str(e)}")

# 展示与校验面板
if st.session_state.current_storyboard:
    col_edit, col_mon = st.columns([3, 2])
    
    with col_edit:
        st.subheader("✍️ 分镜编辑区 (确认序号和字数)")
        # 用户可以在此手动校正 AI 遗漏的序号或过长的句子
        st.session_state.current_storyboard = st.text_area(
            "分镜文案草稿", 
            value=st.session_state.current_storyboard, 
            height=500
        )

    with col_mon:
        st.subheader("📊 实时监控看板")
        lines = [l.strip() for l in st.session_state.current_storyboard.split('\n') if l.strip()]
        
        analysis_data = []
        reconstructed_text = ""
        
        for i, line in enumerate(lines):
            # 正则匹配序号：1. 或者 1、
            match = re.match(r'^(\d+)[.、\s]+(.*)', line)
            if match:
                num, content = match.groups()
                reconstructed_text += content
                char_len = len(content)
            else:
                content = line
                reconstructed_text += content
                char_len = len(content)
                num = "ERR" # 缺失序号标记

            # 评估状态
            if char_len > 40: status = "🔴 过长(>40)"
            elif char_len > 35: status = "🟡 拥挤(>35)"
            elif num == "ERR": status = "⚠️ 缺失序号"
            else: status = "🟢 理想"
            
            analysis_data.append({"序号": num, "内容预览": content[:10]+"...", "字数": char_len, "节奏": status})
        
        # 无损校验
        orig_len = len(st.session_state.original_raw)
        curr_len = len(reconstructed_text)
        if orig_len == curr_len:
            st.success(f"✅ 无损检测：通过 ({curr_len}/{orig_len})")
        else:
            diff = orig_len - curr_len
            st.error(f"⚠️ 丢字警告：原{orig_len}字，现{curr_len}字 (相差{diff}字)")
        
        st.dataframe(pd.DataFrame(analysis_data), use_container_width=True)

    st.divider()

    # ================= 第二阶段：分步描述生成 =================
    st.header("Step 2: 生成画面与视频提示词 (分批)")
    
    char_info = st.text_area("1. 请输入该视频涉及的核心人物描述 (着装、样貌)", 
                            placeholder="例如：林凡：25岁，剑眉星目，穿着深蓝刺绣长衫，腰佩白玉。",
                            height=100)
    
    if char_info:
        # 预处理确认的分镜列表
        confirmed_lines = []
        for l in st.session_state.current_storyboard.split('\n'):
            if l.strip():
                # 提取文案
                m = re.match(r'^(\d+)[.、\s]+(.*)', l.strip())
                confirmed_lines.append(m.group(2) if m else l.strip())
        
        total_shots = len(confirmed_lines)
        curr_p = st.session_state.process_idx
        batch_size = 20
        end_p = min(curr_p + batch_size, total_shots)

        if curr_p < total_shots:
            if st.button(f"🎞️ 生成分镜描述 ({curr_p + 1} - {end_p})"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_text = ""
                    for i, t in enumerate(confirmed_lines[curr_p:end_p]):
                        batch_text += f"分镜{curr_p + i + 1}：{t}\n"
                    
                    step2_prompt = f"""你现在是视觉导演。请根据分镜文案生成提示词。

【角色设定】：
{char_info}

【要求】：
1. 每个分镜必须包含：[画面描述(Midjourney)]、[视频生成(即梦AI)]。
2. **画面描述**：针对Midjourney。描述静态：景别、场景、人物细节、光影、材质。严禁描述行为。
3. **视频生成**：针对即梦AI。描述动态：5秒内的动作流、微表情变化、镜头推移。采用短句堆砌。
4. **单焦原则**：一个分镜专注一个视觉重心，动作连贯。

【待处理文案】：
{batch_text}"""

                    with st.spinner("正在精修视觉提示词..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": step2_prompt}]
                        )
                        st.session_state.batch_results.append(response.choices[0].message.content)
                        st.session_state.process_idx = end_p
                        st.rerun()
                except Exception as e:
                    st.error(f"描述生成失败: {e}")
        else:
            st.success("✅ 全部分镜描述生成完毕！")

        for r_idx, r_text in enumerate(st.session_state.batch_results):
            with st.expander(f"📦 批次 {r_idx+1} 生成结果 (20组)", expanded=True):
                st.markdown(r_text)
