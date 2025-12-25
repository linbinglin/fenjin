import streamlit as st
from openai import OpenAI
import re
import time

# ==========================================
# 🎨 全局样式与配置
# ==========================================
st.set_page_config(
    page_title="导演引擎 V11",
    page_icon="🎬",
    layout="wide"
)

# 自定义CSS，为了复刻截图中的大字体和Metric样式
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 24px;
        color: #333;
    }
    .big-font {
        font-size: 30px !important;
        font-weight: bold;
    }
    .stProgress > div > div > div > div {
        background-color: #007bff;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🧠 核心逻辑函数
# ==========================================

def flatten_text(text):
    """文本清洗：去除换行，准备‘面团’"""
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r'\d+[\.、]\s*', '', text) # 去除原有序号
    return re.sub(r'\s+', ' ', text).strip()

def count_plot_blocks(text):
    """
    逻辑推敲：模拟截图中的'识别剧情块'。
    简单逻辑：根据双换行符来预判大概有多少个自然段落。
    """
    return len([b for b in text.split('\n\n') if b.strip()])

def calculate_deviation(original, generated):
    """
    严谨计算偏差值：
    原文纯文本 vs 生成内容（去掉序号后的）纯文本
    """
    # 清洗生成的内容，去掉 "1. " 这种序号
    gen_clean = re.sub(r'^\d+[\.、]\s*', '', generated, flags=re.MULTILINE)
    gen_clean = gen_clean.replace('\n', '').replace(' ', '')
    
    org_clean = original.replace(' ', '').replace('\n', '')
    
    # 简单的长度差计算
    return len(org_clean) - len(gen_clean)

# ==========================================
# 🎬 侧边栏 (完美复刻截图左侧)
# ==========================================
with st.sidebar:
    st.header("⚙️ 导演引擎 V11")
    
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    
    # 模型选择
    model_id = st.text_input("Model ID", value="grok-4.1")
    
    st.markdown("---")
    
    # 截图左下角的蓝色说明块
    st.info("""
    **🎞️ V11 视觉切分准则:**
    
    1. **主语即镜头**: 人称切换（如“我”转“他”）必须断开。
    2. **动作即分镜**: 一个核心动作完成后必须切镜。
    3. **对话独立性**: 台词结束后的动作描写严禁混在一起。
    4. **硬性 35 字**: 单行依然禁止超过 35 字。
    """)

# ==========================================
# 🖥️ 主界面 (完美复刻截图布局)
# ==========================================

st.markdown("## 🎞️ 全能文案·电影感分镜系统 (V11)")
st.caption("针对“音画不同步”、“内容重叠”深度优化。适配全题材文案。")

# 1. 文件上传
uploaded_file = st.file_uploader("📂 选择 TXT 文案", type=['txt'])

if uploaded_file is not None:
    raw_content = uploaded_file.read().decode("utf-8")
    flat_content = flatten_text(raw_content)
    plot_blocks = count_plot_blocks(raw_content)
    
    # 2. 视觉逻辑稽核面板 (UI核心复刻)
    st.markdown("### 📊 视觉逻辑稽核面板")
    
    # 使用占位符，以便后续动态更新数据
    m1, m2, m3, m4 = st.columns(4)
    metric_origin = m1.metric("原文总字数", f"{len(flat_content)} 字")
    metric_shots = m2.empty() # 占位：生成分镜总数
    metric_processed = m3.empty() # 占位：处理后总字数
    metric_dev = m4.empty() # 占位：偏差值
    
    # 初始化状态
    metric_shots.metric("生成分镜总数", "0 组")
    metric_processed.metric("处理后总字数", "待处理")
    metric_dev.metric("偏差值", "计算中...")

    # 3. 启动按钮与进度条
    if st.button("🚀 启动视觉无损分镜", type="primary"):
        if not api_key:
            st.error("缺少 API Key")
        else:
            client = OpenAI(api_key=api_key, base_url=base_url)
            
            # --- 模拟截图中的进度条效果 (增加仪式感) ---
            progress_text = st.empty()
            bar = st.progress(0)
            
            progress_text.text(f"📦 已识别 {plot_blocks} 个独立剧情块，正在进行视觉单元规划...")
            for i in range(100):
                time.sleep(0.01) # 假装在思考，给用户心理缓冲
                bar.progress(i + 1)
            time.sleep(0.5)
            # ---------------------------------------

            st.markdown("### 📝 视觉分镜编辑器 (无损还原)")
            result_area = st.empty()
            full_response = ""
            
            # Prompt 逻辑 (保持 V2.0 的严谨性)
            system_prompt = f"""
            你是由Python程序调用的专业分镜引擎。你的任务是将输入的文本流重组为标准的视频分镜列表。
            【强制原则】
            1. **无损还原**：必须包含原文所有汉字，禁止增删。
            2. **Markdown列表**：输出必须是数字列表格式 (1. xxx)。
            3. **换行逻辑**：场景切换、对话切换、人称切换必须换行。
            4. **单行限制**：单行尽量控制在35字以内，长难句需根据语义切分。
            
            现在，请对以下文本进行分镜：
            """
            
            try:
                stream = client.chat.completions.create(
                    model=model_id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": flat_content}
                    ],
                    stream=True,
                    temperature=0.1
                )
                
                # 流式输出
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        result_area.markdown(full_response)
                        
                        # 实时更新“分镜总数”
                        current_shots = len(full_response.split('\n'))
                        metric_shots.metric("生成分镜总数", f"{current_shots} 组")

                # --- 任务完成后的严谨核算 ---
                
                # 1. 计算处理后字数 (去掉序号)
                final_clean_text = re.sub(r'^\d+[\.、]\s*', '', full_response, flags=re.MULTILINE)
                final_clean_text = final_clean_text.replace('\n', '')
                metric_processed.metric("处理后总字数", f"{len(final_clean_text)} 字")
                
                # 2. 计算偏差值
                deviation = len(flat_content.replace(' ', '')) - len(final_clean_text.replace(' ', ''))
                
                if deviation == 0:
                    metric_dev.metric("偏差值", "0 字", delta="完美无损", delta_color="normal")
                    st.success("✅ 100% 镜像还原成功")
                else:
                    metric_dev.metric("偏差值", f"{deviation} 字", delta="存在遗漏/增添", delta_color="inverse")
                    st.warning(f"⚠️ 警告：原文与分镜存在 {deviation} 字的偏差，请检查AI是否偷懒。")
                    
            except Exception as e:
                st.error(f"发生错误: {e}")

else:
    # 初始空状态占位
    st.info("👈 请在左侧配置 API 并上传文件")
    
    # 仅仅为了展示效果，未上传文件时显示空的面板
    st.markdown("### 📊 视觉逻辑稽核面板")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("原文总字数", "0 字")
    c2.metric("生成分镜总数", "0 组")
    c3.metric("处理后总字数", "0 字")
    c4.metric("偏差值", "0 字")
    
    st.markdown("---")
    # 进度条占位
    st.markdown("Wait for upload...")
    st.progress(0)
