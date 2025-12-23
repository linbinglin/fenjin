import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="AI电影解说分镜Pro-导演版", layout="wide")

# --- 状态初始化 ---
if 'raw_text' not in st.session_state: st.session_state.raw_text = ""
if 'storyboard_txt' not in st.session_state: st.session_state.storyboard_txt = ""
if 'final_desc' not in st.session_state: st.session_state.final_desc = []
if 'batch_idx' not in st.session_state: st.session_state.batch_idx = 0

# --- 侧边栏 ---
st.sidebar.title("🎬 导演工作台设置")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.title("🎥 AI电影解说全流程导演系统 (高密度版)")
st.info("本系统已更新【35字熔断逻辑】。目标：确保每一帧画面动作完整，且配音不超长。")

# ================= Step 1: 物理粉碎与三维分镜 =================
st.header("Step 1: 文案解构与节奏切割")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    # 【物理粉碎】抹除所有段落，形成纯文字流
    content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    clean_stream = re.sub(r'[\s\n\r\t]+', '', content).strip()
    st.session_state.raw_text = clean_stream
    
    st.write(f"📊 **文案解析成功**：原文共 {len(clean_stream)} 字符。")

    if st.button("🚀 启动智能三维分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 【终极导演指令】
                step1_instruction = f"""你是一名拥有20年剪辑经验的电影解说导演。
现在我给你一段物理粉碎后、没有任何格式的文案流，请进行分镜处理。

### 你的核心分镜技巧：
1. **数字序号**：每一行必须以“数字.”开头（如：1.内容）。
2. **35字硬性熔断（解决拥挤）**：每个分镜文案严格控制在 25-35 字符。**绝对严禁超过40个字符**。如果一句话很长，请在逻辑断点（逗号/感叹号）处强行切开。
3. **视觉动作单一性（解决崩坏）**：
   - 如果一段话包含多个动作（如：推门、坐下、叹气），即使字数没超，也必须切成两个分镜。
   - 确保“即梦AI”在5秒内只需要生成1个核心动作演变。
4. **角色特写逻辑**：只要出现角色对话（双引号内的内容），必须独立分镜。
5. **聚拢平衡**：不要一句一分（如“他走了”这种太碎）。尝试将相关的短动作聚拢到30字左右。
6. **无损要求**：严禁修改、添加或删除任何文字。

待处理文案流：
{clean_stream}"""

                with st.spinner("导演正在进行逐字节奏切分..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你只输出带序号的分镜列表，不准改字。"},
                            {"role": "user", "content": step1_instruction}
                        ],
                        temperature=0 # 强制确定性
                    )
                    st.session_state.storyboard_txt = response.choices[0].message.content
                    st.session_state.final_desc = []
                    st.session_state.batch_idx = 0
            except Exception as e:
                st.error(f"处理失败: {str(e)}")

# 预览区与审计
if st.session_state.storyboard_txt:
    col_edit, col_audit = st.columns([3, 2])
    
    with col_edit:
        st.subheader("✍️ 分镜编辑区 (确认35字原则)")
        final_edit = st.text_area("分镜文案预览", value=st.session_state.storyboard_txt, height=500)
        st.session_state.storyboard_txt = final_edit

    with col_audit:
        st.subheader("📊 节奏审计看板")
        lines = [l.strip() for l in final_edit.split('\n') if l.strip()]
        
        # 丢字检测
        recombined = "".join([re.sub(r'^\d+[\.、\s]+', '', l) for l in lines])
        diff = len(st.session_state.raw_text) - len(recombined)
        
        if diff == 0:
            st.success(f"✅ 文案无损：{len(recombined)} 字")
        else:
            st.error(f"⚠️ 内容异常：差额 {diff} 字 (请检查是否丢字)")

        # 统计分析
        analysis = []
        for i, l in enumerate(lines):
            c = re.sub(r'^\d+[\.、\s]+', '', l)
            ln = len(c)
            if ln > 38: status = "🔴 必断(超长)"
            elif ln < 18: status = "🟡 略碎"
            else: status = "🟢 完美"
            analysis.append({"分镜": i+1, "字数": ln, "评价": status})
        
        st.dataframe(pd.DataFrame(analysis), use_container_width=True)
        st.metric("🎬 分镜总数", f"{len(lines)} 组")

    st.divider()

    # ================= Step 2: 画面与动作逻辑生成 =================
    st.header("Step 2: 生成 AI 画面与即梦AI视频描述")
    
    char_info = st.text_area("1. 录入核心角色视觉设定", 
                            placeholder="描述角色外貌、衣着细节。例如：贵妃：30岁，华丽凤冠，眼神犀利，穿着黄色刺绣襦裙。", 
                            height=100)
    
    if char_info:
        # 提取分镜列表
        clean_lines = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in st.session_state.storyboard_txt.split('\n') if l.strip()]
        total = len(clean_lines)
        idx = st.session_state.batch_idx
        end = min(idx + 20, total)

        if idx < total:
            if st.button(f"🎞️ 生成批次描述 ({idx + 1} - {end})"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_text = "\n".join([f"分镜{i+idx+1}: {t}" for i, t in enumerate(clean_lines[idx:end])])
                    
                    desc_prompt = f"""你现在是视觉导演。请为以下分镜生成MJ提示词和即梦AI视频词。

【角色设定】：{char_info}

【要求】：
1. **画面描述 (MJ)**：描述静态。视角（景别）、环境、人物外貌、精细着装、光影。不准写动作。
2. **视频生成 (即梦AI)**：描述5秒内的动作轨迹。基于文案，描述人物神态如何变化，肢体如何位移。
3. **适配短视频**：采用短句堆砌，确保一个视频分镜只有一个视觉核心。

分镜文案：
{batch_text}"""

                    with st.spinner("AI正在构思视觉演变..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": desc_prompt}]
                        )
                        st.session_state.final_desc.append(response.choices[0].message.content)
                        st.session_state.batch_idx = end
                        st.rerun()
                except Exception as e:
                    st.error(f"生成失败: {e}")
        else:
            st.success("🏁 全部分镜描述已完成！")

        for r in st.session_state.final_desc:
            st.markdown(r)
            st.divider()
