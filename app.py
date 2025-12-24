import streamlit as st
import requests
import time
import re

# --- 页面配置 ---
st.set_page_config(
    page_title="精密分镜助理 Pro Max V4.0", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# --- 样式美化 ---
st.markdown("""
    <style>
    .reportview-container .main .block-container{ max-width: 90%; }
    .stTextArea textarea { font-family: 'Courier New', Courier, monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 侧边栏：核心配置 ---
with st.sidebar:
    st.header("⚙️ 导演级参数配置")
    api_url = st.text_input("1. API 中转地址", value="https://blog.tuiwen.xyz/v1/chat/completions")
    api_key = st.text_input("2. API Key", type="password", help="请输入您的有效 API 密钥")
    
    model_id = st.text_input("3. Model ID", value="grok-4.1", help="手动输入模型名称，如 gpt-4o, claude-3-5-sonnet 等")
    
    st.divider()
    chunk_size = st.slider("4. 逻辑块大小", 500, 2000, 1000, help="处理长文案时的分段长度，建议 800-1000")
    
    st.info("""
    **较真准则：**
    - 每一镜：15-35 字符（约5秒）
    - 严禁：对话与动作混杂
    - 严禁：跨角色/跨场景缝合
    """)

# --- 深度进化的系统提示词 (助理的核心灵魂) ---
SYSTEM_PROMPT = """你是一个极其严谨、甚至偏执的电影解说分镜导演。
你的唯一任务是将提供的文本流拆解为“画面逻辑独立”的分镜列表。

### 强制切割准则（优先级从高到低）：
1. **画面主体切换（绝对硬指标）**：
   - 只要【说话的人】变了，必须另起分镜。
   - 只要从【对白】转为【动作描写】，必须另起分镜。
   - 只要主语发生变化（如从“皇上”的行为转为“我”的反应），必须另起分镜。
   
2. **逻辑逻辑转折**：
   - 场景转换、时空跳跃（如“第一世”到“第二世”）、重大情节转折必须另起分镜。

3. **视听时长平衡（物理约束）**：
   - 在满足前两项的前提下，每个分镜字数严格控制在 15-35 个字符之间。
   - **禁止合并**：严禁为了凑字数将不同角色、不同画面的内容缝合在一起。
   - **允许短镜**：如果是极具张力的短句（如“她死了”），允许独立成镜。

4. **文本零损耗**：
   - 严禁修改、增加、删除、润色原文任何字词。

### 输出格式要求：
- 只输出分镜列表，格式为：序号.内容
- 必须从我指定的【起始序号】开始编号。
- 严禁输出任何引言、解释或括号备注。
"""

# --- 后端工具函数 ---

def clean_and_reformat(raw_text, start_idx):
    """
    较真工具：强行剥离AI可能生成的错误序号，由程序重新赋予全局唯一连续序号。
    """
    lines = raw_text.strip().split('\n')
    valid_shots = []
    current_num = start_idx
    
    for line in lines:
        # 使用正则移除行首的所有数字、点、空格、顿号
        content = re.sub(r'^[0-9\.\s．、]+', '', line).strip()
        if content:
            valid_shots.append(f"{current_num}.{content}")
            current_num += 1
            
    return valid_shots, current_num

def call_ai_api(text_stream, start_num, last_context=""):
    """
    带上下文逻辑的 API 调用
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 构造极度明确的指令
    user_prompt = f"""
【起始序号】：{start_num}
【上下文背景（前情提要）】：...{last_context}
【本次待处理文案流】：
{text_stream}

请严格执行分镜逻辑，确保对话与动作分离，序号连续。
    """
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,  # 降低随机性，确保严谨
        "top_p": 0.1
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"API 请求失败: {str(e)}")
        return None

# --- 主界面 UI ---
st.title("🎬 自动文案分镜拆解程序 V4.0")
st.write("---")

uploaded_file = st.file_uploader("📂 请选择本地 .txt 文案文件", type=['txt'])

if uploaded_file:
    # 预处理文本：移除所有多余换行和空格，变成纯净文本流
    raw_content = uploaded_file.read().decode("utf-8")
    clean_content = "".join(raw_content.split())
    
    st.success(f"文件读取成功！总字数：{len(clean_content)} 字符")
    
    if st.button("🚀 开始自动化精密分镜"):
        if not api_key:
            st.warning("请在左侧边栏输入 API Key")
        else:
            all_final_shots = []
            current_global_idx = 1
            last_bridge_text = ""
            
            # 分段逻辑
            chunks = [clean_content[i:i+chunk_size] for i in range(0, len(clean_content), chunk_size)]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            preview_area = st.empty()
            
            for i, chunk in enumerate(chunks):
                status_text.text(f"⏳ 正在处理第 {i+1}/{len(chunks)} 段逻辑块...")
                
                # 调用 AI
                ai_response = call_ai_api(chunk, current_global_idx, last_bridge_text)
                
                if ai_response:
                    # 强行重排序号，确保全局绝对连续
                    formatted_shots, next_idx = clean_and_reformat(ai_response, current_global_idx)
                    
                    all_final_shots.extend(formatted_shots)
                    current_global_idx = next_idx
                    last_bridge_text = chunk[-40:] # 留 40 字作为下一段的上下文参考
                    
                    # 实时预览
                    preview_area.text_area("实时生成预览 (滚动查看新生成的序号)", "\n".join(all_final_shots), height=300)
                
                # 更新进度
                progress_bar.progress((i + 1) / len(chunks))
            
            status_text.success("✨ 任务全量完成！")
            
            # --- 结果展示与导出 ---
            st.divider()
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("✅ 最终连续分镜脚本")
                final_result_text = "\n".join(all_final_shots)
                st.text_area("全量脚本预览", final_result_text, height=600)
                
            with col2:
                st.subheader("📊 质量合规检查")
                
                # 较真校验统计
                total_s = len(all_final_shots)
                bad_length_shots = [s for s in all_final_shots if len(s.split('.', 1)[-1]) > 35 or len(s.split('.', 1)[-1]) < 15]
                
                st.metric("总分镜数", total_s)
                st.metric("字数异常提醒", len(bad_length_shots))
                
                if bad_length_shots:
                    with st.expander("查看字数异常（需人工关注节奏）"):
                        for bs in bad_length_shots:
                            st.write(bs)
                
                st.download_button(
                    label="📥 导出最终分镜脚本 (.txt)",
                    data=final_result_text,
                    file_name="final_storyboard.txt",
                    mime="text/plain"
                )

# --- 页脚 ---
st.write("---")
st.caption("较真助理提示：如果分镜逻辑依然存在偏差，建议在左侧尝试更换更高级的模型（如 Claude 3.5 Sonnet）。")
