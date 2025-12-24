import streamlit as st
import requests
import time
import re

# --- 页面配置 ---
st.set_page_config(page_title="精密分镜助理 Pro Ultra", layout="wide")
st.title("🎬 电影解说精密分镜系统 - 逻辑闭环版")

# --- 侧边栏配置 ---
with st.sidebar:
    st.header("⚙️ 导演级配置")
    api_url = st.text_input("API 地址", value="https://blog.tuiwen.xyz/v1/chat/completions")
    api_key = st.text_input("API Key", type="password")
    selected_model = st.text_input("Model ID", value="grok-4.1")
    
    st.divider()
    chunk_size = st.slider("逻辑块大小", 300, 1500, 800, help="减小块大小可以提高逻辑严密性")
    st.warning("较真准则：系统已开启格式强制对齐，序号将全局连续。")

# --- 深度进化的导演指令 ---
SYSTEM_PROMPT = """你是一个极其严谨的电影分镜导演。
你的任务是将提供的文本流切分为符合【5秒视听节奏】的分镜。

### 核心操作规约：
1. **全局序号连续性**：你必须从我给出的【起始序号】开始编号，严禁从1重新开始。
2. **5秒黄金律**：
   - 每个分镜文字必须在 20-35 个字符之间。
   - 【强制合并】：如果原文的一句话很短（如“他笑了”），必须强制并入下一个动作或对白中。
   - 【强制拆分】：如果一句话太长（超过35字），必须在逻辑停顿处切开。
3. **零损耗原则**：禁止修改、增加或删除原文中的任何一个字！
4. **分镜逻辑**：
   - 必须在：场景切换、角色切换、重大动作改变、或者字数满35字时，切换到下一个分镜。
5. **纯净输出**：只输出分镜列表，格式严格遵循：序号.内容（例如：12.这是示例分镜文字内容）

### 严禁事项：
- 严禁出现少于15个字的分镜。
- 严禁在分镜中加入（画面描述）等非原文内容。
- 严禁改变故事原有的叙述顺序。
"""

def clean_and_format_results(raw_text, start_num):
    """
    后端强制格式化函数：
    即便AI输出格式有偏差，该函数也会强行将其修正为“序号.内容”
    并确保序号从正确的位置开始。
    """
    lines = raw_text.strip().split('\n')
    formatted_lines = []
    current_idx = start_num
    
    for line in lines:
        # 提取序号之后的所有文字内容，过滤掉AI可能生成的乱码或多余序号
        content = re.sub(r'^\d+[\.．\s、]+', '', line).strip()
        if content:
            formatted_lines.append(f"{current_idx}.{content}")
            current_idx += 1
            
    return formatted_lines, current_idx

def process_logic_flow(full_text):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # 清理原文换行和空格，变成纯净文本流
    clean_text = full_text.replace("\n", "").replace("\r", "").replace(" ", "").strip()
    
    total_shots = []
    current_global_num = 1
    last_context = "" # 存放上一个块的结尾，给AI参考
    
    # 按块处理
    for i in range(0, len(clean_text), chunk_size):
        chunk = clean_text[i : i + chunk_size]
        
        # 构造带有上下文的 User Prompt
        user_content = f"【起始序号】：{current_global_num}\n"
        if last_context:
            user_content += f"【上段结尾参考】：...{last_context}\n"
        user_content += f"【本次需处理原文】：\n{chunk}"
        
        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1
        }
        
        try:
            with st.spinner(f"正在处理第 {current_global_num} 个分镜起的片段..."):
                response = requests.post(api_url, headers=headers, json=payload, timeout=120)
                res_data = response.json()
                raw_output = res_data['choices'][0]['message']['content']
                
                # 后端强制纠偏处理
                formatted_chunk, next_num = clean_and_format_results(raw_output, current_global_num)
                
                total_shots.extend(formatted_chunk)
                current_global_num = next_num
                last_context = chunk[-30:] # 更新上下文参考
                
                # 实时展示
                st.text_area(f"当前处理进度 (序号: {current_global_num-1})", "\n".join(formatted_chunk), height=200)
                
        except Exception as e:
            st.error(f"处理块时发生错误: {str(e)}")
            break
            
    return total_shots

# --- 主界面 ---
uploaded_file = st.file_uploader("选择本地 .txt 文案文件", type=['txt'])

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    
    if st.button("🚀 启动全局逻辑闭环分镜"):
        if not api_key:
            st.error("请填入 API Key")
        else:
            final_storyboard = process_logic_flow(content)
            
            st.divider()
            st.subheader("✅ 最终连续分镜脚本")
            final_text = "\n".join(final_storyboard)
            st.text_area("全量脚本预览：", final_text, height=600)
            
            # 较真校验
            bad_count = 0
            for shot in final_storyboard:
                text_part = shot.split('.', 1)[-1]
                if len(text_part) < 20 or len(text_part) > 35:
                    bad_count += 1
            
            if bad_count > 0:
                st.warning(f"⚠️ 较真提醒：全文共 {len(final_storyboard)} 个分镜，其中 {bad_count} 个字数不在 20-35 之间（已强制序号连续）。")
            else:
                st.success(f"💎 完美达成！共 {len(final_storyboard)} 个分镜，全部符合 5 秒黄金剪辑律且序号连续。")
                
            st.download_button("📥 导出最终分镜脚本", final_text, file_name="final_storyboard.txt")
