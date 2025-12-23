import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="电影解说AI分镜导演Pro", layout="wide")

# --- 初始化全局状态缓存 ---
if 'raw_text_stream' not in st.session_state: st.session_state.raw_text_stream = ""
if 'storyboard_data' not in st.session_state: st.session_state.storyboard_data = ""
if 'batch_descriptions' not in st.session_state: st.session_state.batch_descriptions = []
if 'batch_pointer' not in st.session_state: st.session_state.batch_pointer = 0

# --- 侧边栏 API 配置 ---
st.sidebar.title("⚙️ 导演室配置")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("中转地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("模型名称", value="gpt-4o")

st.title("🎬 电影解说全流程导演系统")
st.caption("版本：3.0 | 核心目标：无损切割、5秒节奏控制、智能语义聚拢")

# ================= 第一阶段：物理粉碎与语义重构 =================
st.header("Step 1: 文案解构与分镜拆解")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    # 【物理粉碎】彻底剥离原文本所有换行，防止AI偷懒参考原结构
    raw_content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    clean_stream = re.sub(r'[\s\n\r\t]+', '', raw_content).strip()
    st.session_state.raw_text_stream = clean_stream
    
    st.success(f"✅ 文本已进入‘无损粉碎’状态，共计 {len(clean_stream)} 字符。AI将无法看到原文段落。")

    if st.button("🚀 启动智能无损分镜"):
        if not api_key:
            st.error("请配置API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 【强化导演指令】
                segment_prompt = f"""你是一名资深电影剪辑导演。现在我给你一段完全没有任何换行和段落的文字流，请将其处理为分镜脚本。

### 核心铁律（违者重罚）：
1. **数字序号**：每一行分镜必须以“数字.”开头，例如：1.文案。
2. **绝对无损**：严禁删除、修改、缩减、添加原文中的任何一个字符。文本必须 100% 完整。
3. **字数红线（解决拥挤）**：每个分镜文案理想长度为 25-35 字符。绝对禁止超过 40 字符（对应5秒配音时长）。
4. **语义聚拢（解决太碎）**：不要一句话分一个镜！如果连续的动作（如：他翻身、下床、穿鞋）在 35 字以内，必须聚拢在一个分镜中。
5. **分镜切分点**：仅在以下情况剪开：
   - 字数即将接近 35 字。
   - 角色切换（换人说话）。
   - 场景突变。

待处理文本流：
{clean_stream}"""

                with st.spinner("导演正在构思分镜节奏..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你只输出带序号的分镜列表，不准有任何解释。"},
                            {"role": "user", "content": segment_prompt}
                        ],
                        temperature=0.1
                    )
                    st.session_state.storyboard_data = response.choices[0].message.content
                    st.session_state.batch_descriptions = []
                    st.session_state.batch_pointer = 0
            except Exception as e:
                st.error(f"分镜生成报错: {str(e)}")

# 第一阶段审计面板
if st.session_state.storyboard_data:
    col_edit, col_audit = st.columns([3, 2])
    
    with col_edit:
        st.subheader("✍️ 分镜编辑区 (确认序号与字数)")
        final_storyboard = st.text_area("分镜文案草稿", value=st.session_state.storyboard_data, height=500)
        st.session_state.storyboard_data = final_storyboard

    with col_audit:
        st.subheader("📊 实时节奏监控")
        lines = [l.strip() for l in final_storyboard.split('\n') if l.strip()]
        
        # 无损校验逻辑
        recombined = "".join([re.sub(r'^\d+[\.、\s]+', '', l) for l in lines])
        orig_len = len(st.session_state.raw_text_stream)
        curr_len = len(recombined)
        
        if orig_len == curr_len:
            st.success(f"✅ 内容校验一致 (共{curr_len}字)")
        else:
            diff = orig_len - curr_len
            st.error(f"⚠️ 丢字警告：原{orig_len}字, 现{curr_len}字 (相差{diff}字)")

        # 节奏评估表格
        analysis = []
        for i, l in enumerate(lines):
            content = re.sub(r'^\d+[\.、\s]+', '', l)
            length = len(content)
            # 这里的评估逻辑是核心
            if length > 35: status = "🔴 太挤(超35字)"
            elif length < 15: status = "🟡 略碎"
            else: status = "🟢 理想"
            analysis.append({"分镜": i+1, "字数": length, "节奏": status})
        st.table(pd.DataFrame(analysis))

    st.divider()

    # ================= 第二阶段：导演提示词生成 =================
    st.header("Step 2: 生成 AI 画面与即梦AI视频描述")
    
    char_desc = st.text_area("1. 录入核心角色设定", 
                            placeholder="请描述角色的样貌、穿着。例如：林凡：剑眉星目，黑色披风，眼神冷酷。",
                            height=100)
    
    if char_desc:
        final_lines = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in st.session_state.storyboard_data.split('\n') if l.strip()]
        total_len = len(final_lines)
        p = st.session_state.batch_pointer
        batch_size = 20
        end_p = min(p + batch_size, total_len)

        if p < total_len:
            if st.button(f"🎬 生成第 {p+1} - {end_p} 组深度描述"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_content = "\n".join([f"分镜{p+i+1}: {t}" for i, t in enumerate(final_lines[p:end_p])])
                    
                    desc_prompt = f"""你现在是视觉导演，负责生成Midjourney和即梦AI的提示词。

### 角色设定：
{char_desc}

### 任务：
1. **画面描述 (MJ)**：描述静态。包含景别、场景细节、人物神态、着装细节、光效。禁止描述任何动作。
2. **视频生成 (即梦AI)**：描述动态。描述这5秒内的动作流。采用短句堆砌。必须包含人物的神态变化和肢体位移。
3. **单焦原则**：一个分镜描述一个核心视觉动作，确保即梦AI能识别。

待处理分镜组：
{batch_content}"""

                    with st.spinner("AI 正在深度解析画面逻辑..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": desc_prompt}]
                        )
                        st.session_state.batch_descriptions.append(response.choices[0].message.content)
                        st.session_state.batch_pointer = end_p
                        st.rerun()
                except Exception as e:
                    st.error(f"描述生成失败: {e}")
        else:
            st.success("✅ 全部分镜描述已生成！")

        for res in st.session_state.batch_descriptions:
            st.markdown(res)
            st.divider()
