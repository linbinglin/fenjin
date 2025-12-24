import streamlit as st
import requests
import json
import pandas as pd
import re

# --- 页面基础配置 ---
st.set_page_config(page_title="严谨版-自动分镜系统 V4.0", layout="wide")

st.markdown("""
    <style>
    .stDataFrame {border: 1px solid #ff4b4b;}
    .reportview-container .main .block-container{padding-top: 2rem;}
    </style>
    """, unsafe_allow_html=True)

# --- 侧边栏：配置参数 ---
with st.sidebar:
    st.title("⚙️ 引擎配置")
    api_key = st.text_input("API Key", type="password")
    base_url = st.text_input("接口地址", value="https://blog.tuiwen.xyz/v1/chat/completions")
    model_id = st.text_input("Model ID", value="gpt-4o")
    
    st.divider()
    max_len = st.slider("单分镜字数上限", 15, 45, 35)
    chunk_size = st.number_input("处理块大小(字数)", value=800, help="为了防止AI幻觉，建议分段处理")

# --- 核心函数：调用AI进行逻辑分镜 ---
def process_text_segment(text, api_key, base_url, model_id, max_char):
    prompt = f"""
你是一个严谨的电影导演。请将下文拆分为[视觉分镜单元]。
【硬性准则】:
1. 无损还原：禁止修改、增加或删除原文中任何一个字。
2. 视觉切分点：
   - 角色对话切换时，必须断开。
   - 场景/时间转移时，必须断开。
   - 核心动作完成时（如：他转身走了），必须断开。
3. 长度控制：
   - 每个分镜必须在15-{max_char}字之间。
   - 如果一句话很短但涉及人称切换，必须独立成行，严禁为了凑字数而跨角色合并。
   - 如果一句话超过{max_char}字，请在不破坏语义的前提下，寻找标点或动词处切分。

【输出格式】:
仅输出分镜内容，分镜之间用'###'分隔，严禁输出序号、严禁换行。

【待处理文本】:
{text}
"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "你是一个只输出文本分割结果的机器人。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=60)
        res_json = response.json()
        return res_json['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error: {str(e)}"

# --- 主程序界面 ---
st.title("🎬 自动分镜无损系统 (严谨助手版)")

uploaded_file = st.file_uploader("上传文案 (.txt)", type=['txt'])

if uploaded_file:
    # 1. 读取并彻底格式化文本
    raw_text = uploaded_file.read().decode("utf-8")
    clean_text = "".join(raw_text.split()) # 抹除原段落
    total_chars = len(clean_text)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("原文总字数", total_chars)

    if st.button("🛠️ 开始执行严谨分镜任务"):
        if not api_key:
            st.error("请先在侧边栏输入 API Key")
        else:
            all_shots = []
            # 2. 分块处理逻辑：解决长文本AI“记不住”和“乱分”的问题
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 将 7000+ 字按 chunk_size 切段
            text_chunks = [clean_text[i:i+chunk_size] for i in range(0, total_chars, chunk_size)]
            
            for idx, chunk in enumerate(text_chunks):
                status_text.text(f"正在处理第 {idx+1}/{len(text_chunks)} 块数据...")
                result = process_text_segment(chunk, api_key, base_url, model_id, max_len)
                
                if "Error:" in result:
                    st.error(result)
                    break
                
                # 分隔并清理
                split_shots = [s.strip() for s in result.split("###") if s.strip()]
                all_shots.extend(split_shots)
                progress_bar.progress((idx + 1) / len(text_chunks))

            # 3. 结果汇总与校验
            processed_text = "".join(all_shots)
            offset = total_chars - len(processed_text)
            
            col2.metric("生成分镜总数", len(all_shots))
            col3.metric("字符偏移(校验)", offset, delta="完美" if offset == 0 else f"缺失{offset}字", delta_color="normal" if offset == 0 else "inverse")

            # 4. 构建展示表格
            df_list = []
            for i, shot in enumerate(all_shots):
                c_len = len(shot)
                df_list.append({
                    "分镜序号": i + 1,
                    "内容": shot,
                    "字数": c_len,
                    "状态": "✅" if 10 <= c_len <= max_len else "⚠️"
                })
            
            df = pd.DataFrame(df_list)

            st.subheader("📝 视觉分镜精修表")
            # 使用 data_editor 实现紧凑排列
            edited_df = st.data_editor(
                df,
                column_config={
                    "分镜序号": st.column_config.NumberColumn(width="small"),
                    "内容": st.column_config.TextColumn(width="large"),
                    "字数": st.column_config.NumberColumn(width="small"),
                    "状态": st.column_config.TextColumn(width="small"),
                },
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True
            )

            # 5. 下载结果
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("💾 导出分镜表 (CSV)", csv, "shots_fixed.csv", "text/csv")

            if offset != 0:
                st.warning("⚠️ 检测到字数偏移，可能是AI在切分时合并或漏掉了标点。建议微调 chunk 大小重新运行。")
