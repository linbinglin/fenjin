import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="AI电影解说导演系统 Pro", layout="wide")

# --- 初始化全局状态 ---
if 'raw_stream' not in st.session_state: st.session_state.raw_stream = ""
if 'storyboard_output' not in st.session_state: st.session_state.storyboard_output = ""
if 'batch_results' not in st.session_state: st.session_state.batch_results = []
if 'current_idx' not in st.session_state: st.session_state.current_idx = 0

# --- 侧边栏 ---
st.sidebar.title("🎬 导演工作台")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("模型 ID", value="gpt-4o")

st.title("📽️ 电影解说全流程导演分镜系统")
st.markdown("---")

# ================= Step 1: 物理拆解与无损分镜 =================
st.header("Step 1: 智能无损分镜拆解")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    # 物理粉碎：合并为一条长字符流
    content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    clean_stream = re.sub(r'[\s\n\r\t]+', '', content).strip()
    st.session_state.raw_stream = clean_stream
    
    st.info(f"📋 **文案指纹已锁定**：原文总计 {len(clean_stream)} 字（已物理脱敏）")

    if st.button("🚀 启动导演思维分镜"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 强化“零容忍”指令：禁止添加任何文字
                director_prompt = f"""你现在是一台高精度的“文案切割复印机”。
你的唯一任务是将以下文案流切割成带序号的分镜。

### 核心切割准则：
1. **禁止原创**：严禁添加、删除或修改原文中的任何一个字符（包括标点）。你只是在文字之间插入换行。
2. **强制序号**：每一行必须以“数字.”开头，例如：1.文案内容
3. **分镜字数均衡（35字原则）**：
   - 目标：每个分镜文案约 25-35 字符（5秒音频）。
   - 禁止太碎：如果一句话只有几个字，必须与后文合并，直到接近30字左右。
   - 禁止拥挤：单行严禁超过 40 字符。
4. **语义切分**：优先在场景切换、对话切换、独立动作完成处切分。

待处理文案流：
{clean_stream}"""

                with st.spinner("AI 正在逐字核对并进行叙事切分..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你只负责无损切割，不准说话，不准改字，不准遗漏。"},
                            {"role": "user", "content": director_prompt}
                        ],
                        temperature=0 # 强制 0 随机性
                    )
                    st.session_state.storyboard_output = response.choices[0].message.content
                    st.session_state.batch_results = []
                    st.session_state.current_idx = 0
            except Exception as e:
                st.error(f"处理失败: {str(e)}")

# 展示预览与精修
if st.session_state.storyboard_output:
    # 1. 统计解析
    lines = [l.strip() for l in st.session_state.storyboard_output.split('\n') if l.strip()]
    total_shots = len(lines)
    
    # 2. 核心数据看板
    st.subheader("📊 分镜审计中心")
    c1, c2, c3 = st.columns(3)
    
    # 解析纯文案用于字数校验
    recombined_text = ""
    analysis_data = []
    for i, line in enumerate(lines):
        # 严格过滤掉序号和特殊字符前缀
        content = re.sub(r'^[\d\s\.、\-:：]+', '', line)
        recombined_text += content
        char_len = len(content)
        # 节奏评价
        if char_len > 38: res = "🔴 太拥挤"
        elif char_len < 18: res = "🟡 略碎"
        else: res = "🟢 理想"
        analysis_data.append({"序号": i+1, "内容": content[:15]+"...", "字数": char_len, "建议": res})

    # 看板指标显示
    c1.metric("🎬 分镜总数", f"{total_shots} 组")
    
    orig_len = len(st.session_state.raw_stream)
    curr_len = len(recombined_text)
    diff = orig_len - curr_len
    
    if diff == 0:
        c2.metric("📋 字数校验", f"{curr_len}/{orig_len}", "✅ 无损", delta_color="normal")
    else:
        c2.metric("📋 字数校验", f"{curr_len}/{orig_len}", f"⚠️ 偏差 {diff} 字", delta_color="inverse")
    
    c3.metric("⏱️ 预估总时长", f"{int(total_shots * 5 / 60)}分{int(total_shots * 5 % 60)}秒")

    # 3. 编辑与详细列表
    col_edit, col_table = st.columns([2, 1])
    with col_edit:
        st.session_state.storyboard_output = st.text_area("✍️ 导演精修区（修改后上方看板会自动刷新）", 
                                                       value=st.session_state.storyboard_output, 
                                                       height=500)
    with col_table:
        st.dataframe(pd.DataFrame(analysis_data), use_container_width=True, height=500)

    st.divider()

    # ================= Step 2: 深度视觉生成 =================
    st.header("Step 2: 生成 AI 画面与视频运动描述")
    char_info = st.text_area("1. 录入核心角色视觉设定", 
                            placeholder="描述外貌、衣着等。例如：林凡：剑眉星目，黑色战术背心。", 
                            height=100)
    
    if char_info:
        # 获取纯净文案列表
        pure_lines = [re.sub(r'^[\d\s\.、\-:：]+', '', l.strip()) for l in st.session_state.storyboard_output.split('\n') if l.strip()]
        total_len = len(pure_lines)
        p = st.session_state.current_idx
        batch = 20
        end_p = min(p + batch, total_len)

        if p < total_len:
            if st.button(f"🎨 生成第 {p+1} - {end_p} 组深度描述"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_content = "\n".join([f"分镜{p+i+1}: {t}" for i, t in enumerate(pure_lines[p:end_p])])
                    
                    prompt = f"""你现在是视觉导演，负责生成提示词。
角色设定：{char_info}

要求：
1. **画面描述 (MJ)**：描述静态。视角、场景、人物细节、光效。禁止描述行为。
2. **视频生成 (即梦AI)**：描述5秒内的动作流。描述微表情和肢体位移。短句堆砌。
3. **单焦原则**：一分镜一核心视觉。

分镜组：
{batch_content}"""

                    with st.spinner("AI正在深度构思画面细节..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        st.session_state.batch_results.append(response.choices[0].message.content)
                        st.session_state.current_idx = end_p
                        st.rerun()
                except Exception as e:
                    st.error(f"失败: {e}")
        else:
            st.success("✅ 全部描述生成完毕")

        for r in st.session_state.batch_results:
            st.markdown(r)
            st.divider()
