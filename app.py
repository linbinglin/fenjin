import streamlit as st
from openai import OpenAI
import os

# 页面配置
st.set_page_config(page_title="文案分镜自动生成器", layout="wide")

# 侧边栏设置
st.sidebar.title("⚙️ API 设置")
api_key = st.sidebar.text_input("请输入 API Key", type="password")
base_url = st.sidebar.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")
model_id = st.sidebar.text_input("Model ID (模型名称)", value="gpt-4o", help="例如：gpt-4o, claude-3-5-sonnet, deepseek-chat")

st.sidebar.markdown("---")
st.sidebar.info("""
**分镜逻辑说明：**
1. 35字内/分镜（约5秒）
2. 动作/场景/对话切换即切分镜
3. 严格保持原文字数和顺序
""")

# 主界面
st.title("🎬 文案分镜自动生成器")
st.caption("上传txt文案，一键生成符合电影解说节奏的分镜脚本")

# 文件上传
uploaded_file = st.file_uploader("选择本地 txt 文件", type=['txt'])

if uploaded_file is not None:
    # 读取内容
    stringio = uploaded_file.getvalue().decode("utf-8")
    
    st.subheader("📄 原始文案预览")
    st.text_area("", value=stringio, height=200, disabled=True)

    if st.button("🚀 开始自动化分镜处理"):
        if not api_key:
            st.error("请先在左侧输入 API Key")
        else:
            try:
                # 初始化客户端
                client = OpenAI(api_key=api_key, base_url=base_url)
                
                with st.spinner('AI 正在深度解析剧情并拆解分镜...'):
                    # 构建 Prompt
                    system_msg = """你是一个优秀的电影解说工作员。
要求：
1. 逐字逐句理解文本内容，对文本进行分段处理。
2. 每个角色对话切换、场景切换、动作画面改变，都必须设定为下一个分镜。
3. 整理后的内容不可遗漏原文中任何一句话、一个字，不能改变原文结构，禁止添加任何原文以外的内容。
4. 严格根据场景转换进行段落分行：另起一行并用数字标号。
5. 每一个分段文案不能太长。因为5秒音频约对应35个字符，请确保每一行文案在35个字符以内，如果原句过长请物理拆分为多行分镜。
6. 忽略用户上传文本原本的换行格式，重新按逻辑和字数限制进行分镜。
输出示例格式：
1.文案内容
2.文案内容"""

                    user_msg = f"请对以下文本进行分镜处理，不要说任何废话，直接输出结果：\n\n{stringio}"

                    # 调用 API
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg}
                        ],
                        temperature=0.3, # 低随机性保证准确度
                    )

                    result = response.choices[0].message.content

                    st.subheader("🎬 分镜处理结果")
                    st.text_area("复制结果", value=result, height=500)
                    
                    # 提供下载
                    st.download_button(
                        label="下载分镜脚本",
                        data=result,
                        file_name="storyboard_result.txt",
                        mime="text/plain"
                    )
            except Exception as e:
                st.error(f"处理出错：{str(e)}")

# 底部运行指引
st.markdown("---")
st.markdown("### 🛠️ 如何部署到 Streamlit Cloud?")
st.code("""
1. 将此代码保存为 app.py
2. 创建 requirements.txt，内容写入：
   streamlit
   openai
3. 将代码上传到 GitHub 仓库
4. 在 Streamlit Cloud 关联此仓库即可在线运行
""", language="markdown")
