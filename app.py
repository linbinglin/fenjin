import streamlit as st
from openai import OpenAI
import io

# 页面配置
st.set_page_config(page_title="电影解说分镜专家系统", layout="wide")

# 初始化 Session State 存储数据
if 'segments' not in st.session_state:
    st.session_state.segments = []  # 存储第一步生成的纯分镜文案
if 'batch_index' not in st.session_state:
    st.session_state.batch_index = 0  # 描述生成的进度计数
if 'final_results' not in st.session_state:
    st.session_state.final_results = []  # 存储生成的详细描述结果

# 侧边栏 API 配置
st.sidebar.title("⚙️ API 设置")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.title("🎬 AI 电影解说全流程分镜工具")

# ================= 第一阶段：纯文案分镜 =================
st.header("第一步：纯文案重新分镜")
uploaded_file = st.file_uploader("上传文案文件 (TXT)", type=['txt'], key="text_uploader")

if uploaded_file:
    # 逻辑：读取并彻底删掉原文所有换行符，变成一整块文本
    content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    scrubbed_content = content.replace("\n", "").replace("\r", "").strip()
    
    if st.button("开始分镜切分"):
        if not api_key:
            st.error("请配置 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                # 严厉的 Step 1 Prompt
                step1_prompt = f"""你是一个优秀的电影解说工作员。
以下文本我已经去掉了所有段落标记，请你逐字逐句理解并重新进行分镜处理。

分镜逻辑（严格执行）：
1. 严禁改动或遗漏原文任何字句。
2. 每一个分镜文案绝对不能超过40个字符（需预留音频5秒时长）。
3. 遇到：场景切换、不同角色说话、画面核心动作改变，必须立即另起一行作为新分镜。
4. 不要输出任何多余的解释，直接输出带序号的分镜列表。

待处理文本：
{scrubbed_content}"""

                with st.spinner("正在重组分镜逻辑..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": step1_prompt}]
                    )
                    res = response.choices[0].message.content
                    # 存入 session，方便第二步调用
                    st.session_state.segments = [line.strip() for line in res.split('\n') if line.strip()]
                    st.session_state.batch_index = 0
                    st.session_state.final_results = []
                    st.success(f"分镜切分完成，共计 {len(st.session_state.segments)} 组。")
            except Exception as e:
                st.error(f"分镜失败: {str(e)}")

# 显示第一步结果
if st.session_state.segments:
    with st.expander("🔍 检查分镜结果（确认合格后进行第二步）", expanded=True):
        for s in st.session_state.segments:
            st.write(s)

    st.divider()

    # ================= 第二阶段：画面描述生成 =================
    st.header("第二步：生成 AI 画面与视频描述")
    
    # 在这里才上传角色信息
    char_info = st.text_area("输入核心人物角色设定", 
                            placeholder="例如：\n赵清月：清冷美人，银丝蝴蝶簪，白色刺绣绫罗纱衣。\n赵灵曦：明艳张扬，杏眼桃腮，黄色妆花襦裙。",
                            key="char_input")
    
    if char_info:
        total_shots = len(st.session_state.segments)
        current_idx = st.session_state.batch_index
        next_batch_size = 20
        end_idx = min(current_idx + next_batch_size, total_shots)

        if current_idx < total_shots:
            if st.button(f"生成第 {current_idx + 1} - {end_idx} 组描述"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    current_batch_text = "\n".join(st.session_state.segments[current_idx:end_idx])
                    
                    # 严厉的 Step 2 Prompt
                    step2_prompt = f"""你现在是视觉导演。请为以下分镜生成Midjourney和即梦AI描述。

角色设定：
{char_info}

要求：
1. 每个分镜必须输出：[文案对比]、[画面描述]、[视频生成]。
2. [画面描述] (Midjourney)：描述场景、人物外表着装、景别、光影。严禁描述动态行为。
3. [视频生成] (即梦AI)：描述具体的镜头动作、人物神态、肢体移动。采用短句堆砌，遵循“单焦原则”（一个镜头只做一个核心动作）。
4. 确保角色穿着在所有分镜中保持一致。

待处理分镜：
{current_batch_text}"""

                    with st.spinner(f"正在生成 {current_idx+1} 批次描述..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": step2_prompt}]
                        )
                        batch_result = response.choices[0].message.content
                        st.session_state.final_results.append(batch_result)
                        st.session_state.batch_index = end_idx
                        st.rerun() # 强制刷新以显示最新结果
                except Exception as e:
                    st.error(f"生成描述失败: {str(e)}")
        else:
            st.success("🎉 所有分镜描述生成完毕！")

        # 结果展示
        for i, res in enumerate(st.session_state.final_results):
            st.subheader(f"📦 批次 {i+1} 结果")
            st.text_area(f"批次 {i+1} 文本 (复制到剪贴板)", res, height=400)
