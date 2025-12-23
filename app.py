import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="AI电影解说导演系统 Pro", layout="wide")

# --- 初始化全局状态 ---
if 'raw_stream' not in st.session_state: st.session_state.raw_stream = "" # 物理粉碎后的原文
if 'storyboard_output' not in st.session_state: st.session_state.storyboard_output = "" # 第一步结果
if 'batch_results' not in st.session_state: st.session_state.batch_results = [] # 第二步结果
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0 # 批次进度

# --- 侧边栏配置 ---
st.sidebar.title("⚙️ 导演中心配置")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("模型 ID", value="gpt-4o")

st.title("🎬 电影解说全流程导演分镜系统")
st.markdown("---")

# ================= 第一阶段：导演思维分镜 =================
st.header("Step 1: 语义聚拢分镜（决定节奏）")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    # 【物理操作】物理剔除所有段落和换行，形成无结构长字符流
    content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    clean_stream = re.sub(r'[\s\n\r\t]+', '', content).strip()
    st.session_state.raw_stream = clean_stream
    
    st.write(f"📝 **字符指纹已锁定**：原文共 {len(clean_stream)} 字。已彻底抹除原段落结构。")

    if st.button("📽️ 启动导演思维分镜"):
        if not api_key:
            st.error("请先输入 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 【核心 Prompt 升级】：强化语义聚拢，严禁丢字
                director_logic = f"""你是一名拥有10年经验的电影剪辑导演。现在我给你一段物理粉碎后、没有任何格式的文案长流。
                
### 你的分镜原则：
1. **聚合优先（解决分镜太碎）**：不要一句话分一个镜！一个分镜代表5秒的叙事空间。如果连续的短句在描述同一个场景或连贯动作（如：他翻开书，皱起眉头，叹了口气），必须聚拢在一个分镜中。
2. **字数红线（解决分镜拥挤）**：每个分镜文案的理想长度在 25-35 字符之间。绝对严禁超过40个字符（超过5秒）。
3. **强制序号**：每一行必须以“数字.”开头，如“1.文案”。
4. **无损切割（严禁改字）**：原文一字不差，不准总结，不准漏字。你只是在文字流中决定哪里该剪开。
5. **切割点逻辑**：仅在“换人说话”、“换地点”、“时间跳跃”或“动作意图彻底改变”且总字数已接近35字时才剪断。

### 待处理文案流：
{clean_stream}"""

                with st.spinner("导演正在深度思考叙事节奏..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你只负责无损分镜切割。"},
                            {"role": "user", "content": director_logic}
                        ],
                        temperature=0.2 # 保证稳定性
                    )
                    st.session_state.storyboard_output = response.choices[0].message.content
                    st.session_state.batch_results = []
                    st.session_state.current_idx = 0
            except Exception as e:
                st.error(f"分镜失败: {str(e)}")

# 第一阶段预览与精修
if st.session_state.storyboard_output:
    col_edit, col_audit = st.columns([3, 2])
    
    with col_edit:
        st.subheader("✍️ 分镜编辑区（可手动校对）")
        edited_text = st.text_area("分镜文案（每行一个5秒镜头）", value=st.session_state.storyboard_output, height=500)
        st.session_state.storyboard_output = edited_text

    with col_audit:
        st.subheader("📊 实时监控与审计")
        lines = [l.strip() for l in edited_text.split('\n') if l.strip()]
        
        # 丢字检测审计
        recombined = "".join([re.sub(r'^\d+[\.、\s]+', '', l) for l in lines])
        orig_len = len(st.session_state.raw_stream)
        curr_len = len(recombined)
        
        if orig_len == curr_len:
            st.success(f"✅ 内容无损：共 {curr_len} 字")
        else:
            st.error(f"⚠️ 丢字预警：原文{orig_len}字，当前{curr_len}字（差额{orig_len - curr_len}）")

        # 节奏评估表格
        analysis = []
        for i, l in enumerate(lines):
            content = re.sub(r'^\d+[\.、\s]+', '', l)
            length = len(content)
            # 这里的评估逻辑是核心：引导用户不要分得太碎
            if length > 40: status = "🔴 太挤(建议拆分)"
            elif length < 20: status = "🟡 太碎(建议合并)"
            else: status = "🟢 理想"
            analysis.append({"序号": i+1, "字数": length, "评价": status})
        
        st.dataframe(pd.DataFrame(analysis), use_container_width=True)

    st.divider()

    # ================= 第二阶段：分步画面描述生成 =================
    st.header("Step 2: 生成 AI 画面与视频运动描述")
    
    char_desc = st.text_area("1. 录入本批次角色视觉设定", 
                            placeholder="描述角色的外貌、穿着、风格。如：赵清月：25岁，肤白如雪，穿着月白色刺绣古装。",
                            height=100)
    
    if char_desc:
        final_lines = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in st.session_state.storyboard_output.split('\n') if l.strip()]
        total_len = len(final_lines)
        c_idx = st.session_state.current_idx
        batch_size = 20
        e_idx = min(c_idx + batch_size, total_len)

        if c_idx < total_len:
            if st.button(f"🎬 生成批次描述 ({c_idx+1} - {e_idx})"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_text = ""
                    for i, t in enumerate(final_lines[c_idx:e_idx]):
                        batch_text += f"分镜{c_idx+i+1}: {t}\n"
                    
                    desc_prompt = f"""你现在是顶级视觉导演。请为以下分镜生成画面提示词。
                    
### 角色设定：
{char_desc}

### 任务要求：
1. **画面描述 (Midjourney)**：静态视觉。描述景别（如：特写）、具体场景细节、人物神态、着装材质、环境光影。**严禁描述动作行为**。
2. **视频生成 (即梦AI)**：动态演变。描述5秒内的动作流。如“人物先是惊愕抬头，随后泪水夺眶而出，镜头缓慢拉近”。
3. **针对聚拢文案的优化**：因为每个分镜包含多句动作，请在视频描述中体现出动作的【连续性】。

待处理分镜组：
{batch_text}"""
                    
                    with st.spinner("AI 正在构思视觉动态..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": desc_prompt}]
                        )
                        st.session_state.batch_results.append(response.choices[0].message.content)
                        st.session_state.current_idx = e_idx
                        st.rerun()
                except Exception as e:
                    st.error(f"描述生成失败: {e}")
        else:
            st.success("✅ 脚本全部描述完成！")

        for r in st.session_state.batch_results:
            st.markdown(r)
            st.divider()
