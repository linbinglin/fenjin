import streamlit as st
from openai import OpenAI
import io
import re

# --- 页面配置 ---
st.set_page_config(page_title="电影解说分镜助手", layout="wide")

# --- 1. 初始化所有状态变量 ---
if 'step' not in st.session_state:
    st.session_state.step = 1  # 步骤控制
if 'raw_text' not in st.session_state:
    st.session_state.raw_text = "" # 原始文本
if 'editor_content' not in st.session_state:
    st.session_state.editor_content = "" # AI初分后的纯净文本
if 'final_numbered' not in st.session_state:
    st.session_state.final_numbered = "" # 最终加了编号的文本

# --- 侧边栏配置 ---
with st.sidebar:
    st.title("⚙️ 设置中心")
    api_key = st.text_input("请输入 API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.divider()
    if st.button("🔄 开启新任务 / 重置"):
        st.session_state.step = 1
        st.session_state.raw_text = ""
        st.session_state.editor_content = ""
        st.session_state.final_numbered = ""
        st.rerun()

st.title("🎬 电影解说·分镜重构工作站")

# --- 辅助函数：文本扁平化 ---
def flatten_text(text):
    # 去除所有换行符和多余空格，保证AI不受原文干扰
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r'\s+', '', text)
    return text

# ==========================================
# 阶段 1：上传文件 & AI 初分镜
# ==========================================
if st.session_state.step == 1:
    st.header("第一步：上传文案并进行 AI 初分")
    
    # 文件上传功能
    uploaded_file = st.file_uploader("选择本地 TXT 文案文件", type=['txt'])
    
    if uploaded_file is not None:
        # 读取并存入状态
        st.session_state.raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
        
        st.success("✅ 文件上传成功！")
        with st.expander("预览原始文案"):
            st.write(st.session_state.raw_text)
            
        # 触发 AI 初分
        if st.button("🚀 开始 AI 逻辑初分", type="primary"):
            if not api_key:
                st.error("请先在左侧配置 API Key")
            else:
                try:
                    with st.spinner("AI 正在深度解析剧情并进行逻辑分段..."):
                        client = OpenAI(api_key=api_key, base_url=base_url)
                        # 强制 AI 扁平化理解并只输出换行
                        clean_input = flatten_text(st.session_state.raw_text)
                        
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": """你是一个专业的电影分镜导演。
                                任务：阅读这段文字流，根据剧情、场景切换、角色对话、动作改变进行分镜换行。
                                要求：
                                1. 每个分镜占一行（直接换行）。
                                2. **绝对禁止**输出任何数字编号、横杠、前缀或后缀。
                                3. **绝对禁止**修改、遗漏或添加原文以外的任何字。
                                4. 只输出纯文字换行后的结果。"""},
                                {"role": "user", "content": clean_input}
                            ],
                            temperature=0.3
                        )
                        st.session_state.editor_content = response.choices[0].message.content
                        st.session_state.step = 2
                        st.rerun()
                except Exception as e:
                    st.error(f"AI 处理出错：{str(e)}")

# ==========================================
# 阶段 2：人工手动精修 (回车拆分/删除合并)
# ==========================================
elif st.session_state.step == 2:
    st.header("第二步：人工自由精修")
    st.info("💡 操作指南：\n1. AI 已为您做了初步分段。\n2. 在需要分镜的地方点击【回车 Enter】即可拆分。\n3. 在需要合并的地方点击【删除 Backspace】即可合并。\n4. 此时不需要管数字编号，只管分段。")
    
    # 使用 text_area 提供编辑功能
    edited_text = st.text_area(
        "分镜编辑器",
        value=st.session_state.editor_content,
        height=500,
        help="在这里直接像编辑文档一样操作"
    )
    
    # 底部操作按钮
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("✅ 确认分段并编号", type="primary"):
            st.session_state.editor_content = edited_text
            try:
                with st.spinner("正在为您自动生成分镜编号..."):
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": """你是一个分镜排版助手。
                            任务：接收文本，在每一行开头增加数字编号（1. 2. 3. ...）。
                            要求：
                            1. 严格按照用户目前的物理换行进行编号。
                            2. 严禁改动原文任何字，严禁改变换行结构。"""},
                            {"role": "user", "content": st.session_state.editor_content}
                        ],
                        temperature=0.1
                    )
                    st.session_state.final_numbered = response.choices[0].message.content
                    st.session_state.step = 3
                    st.rerun()
            except Exception as e:
                st.error(f"编号生成失败：{e}")
    with col_btn2:
        if st.button("⬅️ 返回上一步重新上传"):
            st.session_state.step = 1
            st.rerun()

# ==========================================
# 阶段 3：最终产出与下载
# ==========================================
elif st.session_state.step == 3:
    st.header("第三步：最终分镜定稿")
    
    st.text_area("生成的分镜结果", st.session_state.final_numbered, height=500)
    
    col_final1, col_final2 = st.columns(2)
    with col_final1:
        st.download_button(
            label="📥 下载最终分镜稿 (TXT)",
            data=st.session_state.final_numbered,
            file_name="分镜结果.txt",
            mime="text/plain",
            use_container_width=True
        )
    with col_final2:
        if st.button("⬅️ 返回修改分段", use_container_width=True):
            st.session_state.step = 2
            st.rerun()

# --- 底部版权/说明 ---
st.divider()
st.caption("2025 AI 文案分镜重构助手 | 适配第三方 API | 流程化协作模式")
