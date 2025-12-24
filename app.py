import streamlit as st
import requests
import re
import pandas as pd

st.set_page_config(page_title="电影解说无损分镜系统 V2.0", layout="wide")

# 自定义 CSS 压缩 UI 间距
st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stDataFrame {border: 1px solid #e6e9ef;}
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ 严谨模式引擎")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.divider()
    max_chars = st.slider("单镜头字数上限", 15, 50, 35)
    st.warning("较真助理提示：35字约等于5秒语音。")

st.title("🎬 电影解说专业分镜工作台")

uploaded_file = st.file_uploader("上传文案 (.txt)", type=['txt'])

if uploaded_file:
    # 预处理：彻底清洗干扰字符
    raw_text = uploaded_file.read().decode("utf-8")
    clean_text = "".join(raw_text.split())
    
    c1, c2, c3 = st.columns(3)
    c1.metric("原文总字数", len(clean_text))

    if st.button("🛠️ 执行逻辑分镜拆解"):
        if not api_key:
            st.error("请配置侧边栏 API Key")
        else:
            # 升级后的暴力指令集
            prompt = f"""
            你是一个电影剪辑大师。你的任务是将长文本拆分为分镜文案。
            
            【核心原则】
            1. 严禁修改、添加、删除原文任何字符！
            2. 严禁输出任何多余的文字（如“分镜1”、“场景”等）。
            3. 必须保持原文顺序。
            
            【分镜逻辑】
            - 目标：将长句拆分为适合5秒展示的视觉单元。
            - 长度：每个单元必须在 15 到 {max_chars} 个字符之间。
            - 切分点：优先在标点处切分，其次在主谓宾结构完成处切分。
            
            【输出格式】
            单元1###单元2###单元3...
            (注意：仅使用 ### 作为分隔符，不要换行，不要序号)

            【输入文本】
            {clean_text}
            """

            try:
                with st.spinner("正在进行深度逻辑重组..."):
                    headers = {"Authorization": f"Bearer {api_key}"}
                    data = {
                        "model": model_id,
                        "messages": [{"role": "system", "content": "你是一个只输出原文分隔结果的机器人。"},
                                     {"role": "user", "content": prompt}],
                        "temperature": 0.0 # 强制要求确定性，消除幻觉
                    }
                    
                    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data)
                    raw_output = response.json()['choices'][0]['message']['content'].strip()
                    
                    # 逻辑处理：解析分割后的结果
                    shots = raw_output.split("###")
                    
                    # 构建高密度数据表
                    df_data = []
                    current_count = 0
                    for i, shot in enumerate(shots):
                        shot_content = shot.strip()
                        if not shot_content: continue
                        df_data.append({
                            "序号": i + 1,
                            "分镜文案内容": shot_content,
                            "字数": len(shot_content),
                            "预计时长": f"{len(shot_content)/7:.1f}s" # 假设语速为7字/秒
                        })
                        current_count += len(shot_content)

                    # 渲染数据看板
                    processed_text = "".join([d['分镜文案内容'] for d in df_data])
                    offset = len(clean_text) - len(processed_text)
                    
                    c2.metric("最终分镜总数", len(df_data))
                    c3.metric("字符偏移(校验)", offset, delta="-异常" if offset != 0 else "完美", delta_color="inverse")

                    if offset != 0:
                        st.error(f"严重警告：字符不匹配！缺失字符：{offset}")
                        with st.expander("查看差异对比"):
                            st.write("原文前50字：", clean_text[:50])
                            st.write("生成前50字：", processed_text[:50])

                    # 高效 UI 展示：使用 Data Editor
                    st.subheader("📝 视觉分镜精修表")
                    edited_df = st.data_editor(
                        df_data,
                        column_config={
                            "序号": st.column_config.NumberColumn(width="small"),
                            "分镜文案内容": st.column_config.TextColumn(width="large"),
                            "字数": st.column_config.BarChartColumn(y_min=0, y_max=max_chars),
                        },
                        use_container_width=True,
                        num_rows="dynamic"
                    )
                    
                    # 导出按钮
                    st.download_button(
                        "💾 导出分镜表 (CSV)",
                        pd.DataFrame(edited_df).to_csv(index=False),
                        "storyboard.csv"
                    )

            except Exception as e:
                st.error(f"处理失败：{str(e)}")
