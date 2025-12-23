import streamlit as st
import requests
import json
import re

# 页面配置
st.set_page_config(page_title="文案自动化分镜工具", layout="wide")

st.title("🎬 文案自动分镜应用")
st.caption("输入纯文本，自动根据剧情、动作、对话进行分镜切割")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ API 配置")
    base_url = st.text_input("中转接口地址", value="https://blog.tuiwen.xyz/v1")
    api_key = st.text_input("API Key", type="password")
    model_id = st.text_input("Model ID", value="gpt-4o", help="例如：deepseek-chat, gpt-4o, claude-3-5-sonnet")
    
    st.divider()
    max_chars_per_shot = st.slider("每个分镜建议最大字数", 10, 50, 35)

# 主界面布局
col1, col2 = st.columns(2)

original_text = ""

with col1:
    st.subheader("1. 上传与处理")
    uploaded_file = st.file_uploader("选择本地 TXT 文件", type=['txt'])
    
    if uploaded_file is not None:
        raw_content = uploaded_file.read().decode("utf-8")
        
        # 功能：去除原文所有段落/换行，防止AI偷懒
        clean_text = "".join(raw_content.split())
        original_word_count = len(clean_text)
        
        st.info(f"✅ 文件已上传 | 原文总字数（已去空格）：{original_word_count}")
        st.text_area("预处理后的文本流（已去除段落）：", clean_text, height=200)
        
        if st.button("🚀 开始生成分镜"):
            if not api_key:
                st.error("请输入 API Key")
            else:
                # 构造 Prompt
                system_prompt = f"""你是一个优秀的电影解说工作员和分镜师。
                任务：将用户提供的文案切分为分镜脚本。
                规则：
                1. 严格逐字逐句处理，严禁遗漏、修改或添加原文以外的任何文字。
                2. 触发逻辑：每个角色对话切换、场景切换、动作画面改变，必须另起一行作为一个新分镜。
                3. 字数限制：每个分镜文案长度严格控制在 {max_chars_per_shot} 个字符以内（对应5秒音频）。
                4. 输出格式：每行一个分镜，开头使用数字编号，如：1. 内容... 2. 内容...
                5. 严禁进行总结，必须保留原文所有细节。"""
                
                user_content = f"待处理文本流：\n{clean_text}"
                
                try:
                    with st.spinner("AI 正在分析剧情并生成分镜..."):
                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "model": model_id,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_content}
                            ],
                            "temperature": 0.3 # 降低随机性，保证不丢字
                        }
                        
                        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload)
                        res_json = response.json()
                        result = res_json['choices'][0]['message']['content']
                        
                        st.session_state['result'] = result
                except Exception as e:
                    st.error(f"出错啦：{str(e)}")

with col2:
    st.subheader("2. 分镜输出结果")
    if 'result' in st.session_state:
        output_text = st.session_state['result']
        st.text_area("分镜脚本：", output_text, height=450)
        
        # 字数统计逻辑：提取分镜中的纯文字，去掉数字和换行
        clean_output = re.sub(r'\d+\.', '', output_text) # 去掉数字编号
        clean_output = "".join(clean_output.split())     # 去掉空格和换行
        output_word_count = len(clean_output)
        
        # 数据看板
        c1, c2, c3 = st.columns(3)
        c1.metric("原文总字数", original_word_count)
        c2.metric("输出总字数", output_word_count)
        diff = output_word_count - original_word_count
        c3.metric("字数差异", diff, delta_color="inverse" if diff != 0 else "normal")
        
        if diff != 0:
            st.warning(f"⚠️ 注意：输出字数与原文相差 {abs(diff)} 字，请检查是否有遗漏或重复。")
        else:
            st.success("✨ 校验通过：字数与原文完全一致！")
            
        st.download_button("下载分镜脚本", output_text, file_name="storyboard.txt")
