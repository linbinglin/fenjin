import streamlit as st
from openai import OpenAI
import io
import re
import pandas as pd

st.set_page_config(page_title="AI电影解说分镜Pro", layout="wide")

# --- 初始化 Session State ---
if 'original_text' not in st.session_state: st.session_state.original_text = ""
if 'storyboard_draft' not in st.session_state: st.session_state.storyboard_draft = ""
if 'final_results' not in st.session_state: st.session_state.final_results = []
if 'current_batch' not in st.session_state: st.session_state.current_batch = 0

# --- 侧边栏 ---
st.sidebar.title("🎬 导演工作台配置")
api_key = st.sidebar.text_input("输入 API Key", type="password")
base_url = st.sidebar.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID", value="gpt-4o")

st.title("🎥 AI电影解说全流程导演系统")
st.info("步骤：1. 上传并生成分镜草稿 -> 2. 人工微调分镜 -> 3. 输入角色设定生成AI画面描述。")

# ================= 第一阶段：物理粉碎与智能分镜 =================
st.header("Step 1: 剧情解构与分镜拆解")

uploaded_file = st.file_uploader("上传文案 (TXT)", type=['txt'])

if uploaded_file:
    # 【物理粉碎】彻底剥离原文本所有换行和段落，防止AI参考原结构
    raw_content = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    clean_stream = re.sub(r'\s+', '', raw_content).strip()
    st.session_state.original_text = clean_stream
    
    st.write(f"📊 **文案解析成功**：原文共 {len(clean_stream)} 个字符（已剔除原段落格式）。")

    if st.button("🚀 启动导演思维分镜"):
        if not api_key:
            st.error("请在左侧配置 API Key")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                # 深度导演指令 - 解决太碎/太挤/序号/偷懒问题
                director_logic_prompt = f"""你是一名资深电影剪辑师。现在我给你一段【完全没有段落】的文案流，请你进行分镜处理。

### 你的核心分镜技巧：
1. **强制数字序号**：每一行分镜必须以“数字.”开头，如：1.内容。
2. **拒绝机械切割**：35个字是视频生成的时长上限（约5秒），但不是切割的唯一标准。
3. **分镜平衡艺术（重点）**：
   - **语义聚拢（防止太碎）**：如果连续的短句描述的是同一个角色的连贯动作（如：他起身、开门、走出去），请合并在一个分镜内。不要让画面闪烁太快。
   - **逻辑切分点**：当遇到“角色对话切换”、“场景转移”、“时间大幅跳跃”或“动作意图彻底改变”时，必须立即开启新分镜。
   - **拥挤度控制**：如果一句话超过35个字，观察是否有标点或逻辑断点。如果没有，为了视频时长，必须强行切分为两个有关联的分镜。
4. **无损要求**：严禁更改、删除或添加任何原文文字。你只负责决定在哪里剪一刀。

### 待处理文案流：
{clean_stream}"""

                with st.spinner("导演正在深度思考剧情节奏..."):
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": "你是一个严格的电影分镜导演。只输出带序号的分镜列表，不准有任何解释。"},
                            {"role": "user", "content": director_logic_prompt}
                        ],
                        temperature=0.3
                    )
                    st.session_state.storyboard_draft = response.choices[0].message.content
                    st.session_state.final_results = []
                    st.session_state.current_batch = 0
            except Exception as e:
                st.error(f"分镜失败: {str(e)}")

# 展示分镜区与监控
if st.session_state.storyboard_draft:
    col_edit, col_mon = st.columns([3, 2])
    
    with col_edit:
        st.subheader("✍️ 分镜精修区 (可手动合并或拆分)")
        # 这里用户可以对AI的结果进行最后的微调
        edited_text = st.text_area("分镜文案草稿", value=st.session_state.storyboard_draft, height=500)
        st.session_state.storyboard_draft = edited_text

    with col_mon:
        st.subheader("📈 节奏监控看板")
        # 解析数据
        lines = [l.strip() for l in edited_text.split('\n') if l.strip()]
        rebuilt_text = ""
        analysis_data = []
        
        for i, line in enumerate(lines):
            # 提取序号后的纯内容
            content = re.sub(r'^\d+[\.、\s]+', '', line)
            rebuilt_text += content
            length = len(content)
            
            # 状态评估
            if length > 40: status = "🔴 太挤(超5s)"
            elif length < 12: status = "🟡 略碎"
            else: status = "🟢 理想"
            
            analysis_data.append({"分镜": i+1, "字数": length, "评价": status})
        
        # 无损校验：对比原文字符流和分镜后的字符流
        orig_len = len(st.session_state.original_text)
        curr_len = len(rebuilt_text)
        
        if orig_len == curr_len:
            st.success(f"✅ 无损检测通过 ({curr_len}字)")
        else:
            diff = orig_len - curr_len
            st.error(f"⚠️ 文本不匹配！原:{orig_len}字, 现:{curr_len}字 (差额:{diff})")
            st.info("若差额不为0，说明AI或人工编辑时删减了文字。")
            
        st.table(pd.DataFrame(analysis_data))

    st.divider()

    # ================= 第二阶段：分步画面描述生成 =================
    st.header("Step 2: 生成 AI 画面与视频描述")
    
    char_info = st.text_area("1. 输入核心人物视觉设定", 
                            placeholder="描述角色外貌、衣着。例如：赵大帅：50岁，两撇胡须，身穿深蓝色军装，眼神威严。", 
                            height=100)
    
    if char_info:
        # 获取最终分镜列表
        final_list = [re.sub(r'^\d+[\.、\s]+', '', l.strip()) for l in st.session_state.storyboard_draft.split('\n') if l.strip()]
        total_len = len(final_list)
        curr_idx = st.session_state.current_batch
        batch_size = 20
        end_idx = min(curr_idx + batch_size, total_len)

        if curr_idx < total_len:
            if st.button(f"🎬 生成第 {curr_idx+1} - {end_idx} 组画面描述"):
                try:
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    batch_content = ""
                    for i, t in enumerate(final_list[curr_idx:end_idx]):
                        batch_content += f"分镜{curr_idx+i+1}：{t}\n"
                    
                    desc_prompt = f"""你现在是视觉导演，负责生成Midjourney画面描述词和即梦AI视频动作词。

【核心角色设定】：
{char_info}

【任务要求】：
1. **画面描述 (MJ)**：仅描述静态。包含：景别（特写/全景）、人物精确外貌着装、环境氛围、光影风格。
2. **视频生成 (即梦AI)**：针对这5秒内的文案内容，描述动态。包含：人物微表情演变、肢体动作链、镜头运动。
3. **单焦原则**：一个分镜专注1-2个核心动作，采用短句堆砌，确保即梦AI能识别。

【待处理分镜组】：
{batch_content}"""

                    with st.spinner("AI正在设计视觉细节..."):
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[{"role": "user", "content": desc_prompt}]
                        )
                        st.session_state.final_results.append(response.choices[0].message.content)
                        st.session_state.current_batch = end_idx
                        st.rerun()
                except Exception as e:
                    st.error(f"描述生成失败: {str(e)}")
        else:
            st.success("🏁 所有分镜描述生成完毕！")

        for r in st.session_state.final_results:
            st.markdown(r)
            st.divider()
