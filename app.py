import streamlit as st
from openai import OpenAI
import io
import re

# --- 页面配置 ---
st.set_page_config(page_title="电影解说分镜助手-专业版", layout="wide")

# --- 1. 初始化 Session State ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'raw_text' not in st.session_state:
    st.session_state.raw_text = ""
if 'draft_with_numbers' not in st.session_state:
    st.session_state.draft_with_numbers = ""
if 'final_output' not in st.session_state:
    st.session_state.final_output = ""

# --- 侧边栏设置 ---
with st.sidebar:
    st.title("⚙️ 控制台")
    api_key = st.text_input("请输入 API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.divider()
    if st.button("🔄 开启新任务 / 重置"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.title("🎬 电影解说·分镜精修工作站")

# --- 辅助函数：彻底清洗段落 ---
def flatten_text(text):
    # 去除所有换行和冗余空格，强制AI重新通过剧情理解来分镜
    text = text.replace("\n", "").replace("\r", "")
    text = re.sub(r'\s+', '', text)
    return text

# ==========================================
# 阶段 1：上传与带编号初分
# ==========================================
if st.session_state.step == 1:
    st.header("第一步：上传文案并生成初稿")
    
    uploaded_file = st.file_uploader("选择本地 TXT 文案文件", type=['txt'])
    
    if uploaded_file:
        st.session_state.raw_text = io.StringIO(uploaded_file.getvalue().decode("utf-8")).read()
        st.success("✅ 文件已读取")
        
        if st.button("🚀 生成带编号初版分镜", type="primary"):
            if not api_key:
                st.error("请先配置 API Key")
            else:
                try:
                    with st.spinner("AI 正在深度解析剧情并进行逻辑分镜..."):
                        client = OpenAI(api_key=api_key, base_url=base_url)
                        clean_input = flatten_text(st.session_state.raw_text)
                        
                        response = client.chat.completions.create(
                            model=model_id,
                            messages=[
                                {"role": "system", "content": """你是一个资深的电影解说工作员。
                                任务：阅读文字流，根据剧情、场景切换、角色对话、动作改变进行分镜。
                                要求：
                                1. 严格使用数字编号格式，如 1. 2. 3. 
                                2. 每行一个分镜，每个分镜建议控制在35字左右以对齐5秒音频，但以逻辑完整为先。
                                3. 严禁遗漏原文任何一个字，严禁修改文字顺序。
                                4. 严禁添加任何原文以外的描述性内容。"""},
                                {"role": "user", "content": f"请对以下文案进行带编号的分镜处理：\n\n{clean_input}"}
                            ],
                            temperature=0.3
                        )
                        st.session_state.draft_with_numbers = response.choices[0].message.content
                        st.session_state.step = 2
                        st.rerun()
                except Exception as e:
                    st.error(f"处理出错：{e}")

# ==========================================
# 阶段 2：人工精修 (在带编号的基础上修改)
# ==========================================
elif st.session_state.step == 2:
    st.header("第二步：人工自由精修")
    st.info("💡 此时每一行都有编号。你可以：\n1. 按回车【Enter】拆分（新行不需要写编号，AI稍后会自动补齐）。\n2. 按【删除键】合并（把原本带编号的行合上来即可）。\n3. 确认所有文字一字未差。")
    
    edited_text = st.text_area(
        "分镜编辑器",
        value=st.session_state.draft_with_numbers,
        height=500
    )
    
    col_step2_1, col_step2_2 = st.columns([1, 5])
    with col_step2_1:
        if st.button("✅ 完成精修，重排编号", type="primary"):
            st.session_state.draft_with_numbers = edited_text
            try:
                with st.spinner("正在扫描分段结构并重新对齐编号..."):
                    client = OpenAI(api_key=api_key, base_url=base_url)
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": """你是一个极其严谨的分镜排版助手。
                            任务：接收用户修改后的分镜，清理掉杂乱的旧编号，并根据现在的物理换行重新进行 1. 2. 3. 排序。
                            要求：
                            1. 保持用户现在的换行结构，一行即一个编号。
                            2. 严禁修改原文任何文字，严禁合并或拆分用户已经定好的段落。
                            3. 输出结果必须干净、整齐。"""},
                            {"role": "user", "content": st.session_state.draft_with_numbers}
                        ],
                        temperature=0.1
                    )
                    st.session_state.final_output = response.choices[0].message.content
                    st.session_state.step = 3
                    st.rerun()
            except Exception as e:
                st.error(f"重排失败：{e}")
    with col_step2_2:
        if st.button("⬅️ 返回重传"):
            st.session_state.step = 1
            st.rerun()

# ==========================================
# 阶段 3：最终产出
# ==========================================
elif st.session_state.step == 3:
    st.header("第三步：最终分镜定稿")
    
    st.text_area("最终结果", st.session_state.final_output, height=500)
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 下载最终分镜 TXT", st.session_state.final_output, file_name="电影分镜定稿.txt")
    with c2:
        if st.button("⬅️ 返回修改分段"):
            st.session_state.step = 2
            st.rerun()

st.divider()
st.caption("2025 AI文案分镜工作站 | 逻辑：带编号初分 -> 人工合并拆分 -> 自动序列化重排")
