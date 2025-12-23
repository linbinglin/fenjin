import streamlit as st
from openai import OpenAI
import re

# 页面配置
st.set_page_config(page_title="高级解说分镜师 Pro", layout="wide")

# 侧边栏：API 与 模型配置
st.sidebar.title("⚙️ 系统配置")
api_key = st.sidebar.text_input("1. 输入 API Key", type="password")
base_url = st.sidebar.text_input("2. 中转接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("3. Model ID (自定义模型名称)", value="gpt-4o")

st.sidebar.markdown("---")
st.sidebar.warning("""
**💡 分镜核心准则：**
- 每个分镜 < 35 字符（约 5 秒）
- 动作变、镜头变、台词变 = 换行
- 严禁删改、增添原文任何文字
""")

# 主界面
st.title("🎬 电影解说·万能自动分镜系统")
st.info("本系统会强制打乱原文段落，由 AI 重新根据电影解说节奏进行 1:1 像素级分镜。")

# 1. 文件上传
uploaded_file = st.file_uploader("📂 上传本地文案文件 (txt格式)", type=['txt'])

if uploaded_file is not None:
    # 读取原文
    raw_content = uploaded_file.getvalue().decode("utf-8")
    
    # 【关键处理】删除原文所有换行和多余空格，防止 AI “偷懒”参考原段落
    processed_content = "".join(raw_content.split())
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📝 原始文案（已去段落处理）")
        st.text_area("为了防止AI参考原段落，系统已将文本合并：", value=processed_content, height=300)

    if st.button("🔥 生成深度分镜脚本"):
        if not api_key:
            st.error("请先在左侧配置 API Key！")
        else:
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                with st.spinner('正在进行逐字逻辑拆解...'):
                    # 极其严格的 Prompt 指令
                    system_prompt = f"""你是一个顶级的电影解说分镜专家。
你的任务是将我提供的“文字墙”文案重新拆解为适合视频剪辑的分镜脚本。

【执行逻辑 - 优先级排序】：
1. 字符限制：每一行（每一个分镜）的文字绝对不能超过 35 个字符。这是为了配合 5 秒的配音。
2. 强制切分点：
   - 当画面中的“动作动作”发生改变时，必须切换分镜。
   - 当角色开始说“对话”时，必须切换分镜。
   - 当“场景/环境”发生变化时，必须切换分镜。
3. 文本保真度：严禁删除原文中的任何一个字！严禁添加任何原文以外的废话！严禁调整文字顺序！
4. 结构重组：彻底忽略原文的段落。根据故事情节的节奏，重新排列成数字编号列表。

【输出格式】：
1.文案内容
2.文案内容
3.文案内容
...以此类推。"""

                    user_prompt = f"请对以下无分段文本进行深度分镜拆解：\n\n{processed_content}"

                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1, # 极低随机性，确保严格执行字数要求
                    )

                    st.session_state.result = response.choices[0].message.content

                with col2:
                    st.subheader("🎞️ AI 深度分镜结果")
                    st.text_area("分镜结果：", value=st.session_state.result, height=500)
                    
                    st.download_button(
                        label="💾 下载最终分镜脚本",
                        data=st.session_state.result,
                        file_name="storyboard_pro.txt",
                        mime="text/plain"
                    )
            except Exception as e:
                st.error(f"发生错误：{str(e)}")

# 底部部署指引
with st.expander("🛠️ 开发者部署指南"):
    st.code("""
# 1. 准备 requirements.txt
streamlit
openai

# 2. 将代码保存为 app.py 上传 GitHub
# 3. 在 Streamlit Cloud 关联仓库并运行
    """, language="markdown")
