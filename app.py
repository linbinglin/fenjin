import streamlit as st
import json
import time
import re
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime

# ============================================================
# 页面配置
# ============================================================
st.set_page_config(
    page_title="影视化视觉翻译引擎 V3.2",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 本地自动保存/恢复系统（防数据丢失）
# ============================================================
AUTOSAVE_FILE = "autosave_data.json"

def auto_save():
    """将关键数据自动保存到本地文件"""
    try:
        data = {
            "chapters": st.session_state.get("chapters", {}),
            "chapter_order": st.session_state.get("chapter_order", []),
            "current_step": st.session_state.get("current_step", 0),
            "current_episode": st.session_state.get("current_episode", 1),
            "global_analysis": st.session_state.get("global_analysis", ""),
            "opening_designs": st.session_state.get("opening_designs", ""),
            "episodes": {str(k): v for k, v in st.session_state.get("episodes", {}).items()},
            "review_results": {str(k): v for k, v in st.session_state.get("review_results", {}).items()},
            "memory": st.session_state.get("memory", {}),
            "messages": st.session_state.get("messages", []),
            "chat_history": st.session_state.get("chat_history", []),
            "save_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with open(AUTOSAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def auto_restore():
    """从本地文件恢复数据（仅当session_state中数据为空时）"""
    if not os.path.exists(AUTOSAVE_FILE):
        return False
    # 如果已经有章节或剧本数据，不需要恢复
    if st.session_state.get("chapters") and len(st.session_state["chapters"]) > 0:
        return False
    if st.session_state.get("episodes") and len(st.session_state["episodes"]) > 0:
        return False
    try:
        with open(AUTOSAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 检查备份是否有实际数据
        has_data = (
            len(data.get("chapters", {})) > 0 or
            len(data.get("episodes", {})) > 0 or
            data.get("global_analysis", "") != ""
        )
        if not has_data:
            return False
        # 恢复数据
        if data.get("chapters"):
            st.session_state["chapters"] = data["chapters"]
        if data.get("chapter_order"):
            st.session_state["chapter_order"] = data["chapter_order"]
        if data.get("current_step"):
            st.session_state["current_step"] = data["current_step"]
        if data.get("current_episode"):
            st.session_state["current_episode"] = data["current_episode"]
        if data.get("global_analysis"):
            st.session_state["global_analysis"] = data["global_analysis"]
        if data.get("opening_designs"):
            st.session_state["opening_designs"] = data["opening_designs"]
        if data.get("episodes"):
            st.session_state["episodes"] = {int(k): v for k, v in data["episodes"].items()}
        if data.get("review_results"):
            st.session_state["review_results"] = {int(k): v for k, v in data["review_results"].items()}
        if data.get("memory"):
            st.session_state["memory"] = data["memory"]
        if data.get("messages"):
            st.session_state["messages"] = data["messages"]
        if data.get("chat_history"):
            st.session_state["chat_history"] = data["chat_history"]
        return True
    except Exception:
        return False

def clear_autosave():
    """清除本地备份文件"""
    try:
        if os.path.exists(AUTOSAVE_FILE):
            os.remove(AUTOSAVE_FILE)
    except Exception:
        pass

# ============================================================
# CSS样式
# ============================================================
st.markdown("""
<style>
    .block-container { padding: 1.5rem 2rem 2rem 2rem; max-width: 1200px; }
    .header-bar {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 50%, #2b6cb0 100%);
        border-radius: 12px; padding: 20px 28px; margin-bottom: 24px;
        color: white; display: flex; justify-content: space-between; align-items: center;
        flex-wrap: wrap; gap: 10px;
    }
    .header-left .header-title { font-size: 1.6rem; font-weight: 700; margin: 0; letter-spacing: 1px; }
    .header-left .header-sub { font-size: 0.78rem; opacity: 0.8; margin-top: 4px; }
    .header-badge {
        background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25);
        border-radius: 20px; padding: 6px 16px; font-size: 0.75rem; color: white;
    }
    .step-indicator {
        display: flex; gap: 0; margin: 0 0 20px 0; background: #f7f8fa;
        border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0;
    }
    .step-item {
        flex: 1; text-align: center; padding: 12px 8px; font-size: 0.8rem;
        font-weight: 500; color: #718096; border-right: 1px solid #e2e8f0; transition: all 0.3s;
    }
    .step-item:last-child { border-right: none; }
    .step-item.active { background: #ebf4ff; color: #2b6cb0; font-weight: 600; }
    .step-item.done { background: #f0fff4; color: #276749; }
    .step-num {
        display: inline-block; width: 22px; height: 22px; border-radius: 50%;
        background: #cbd5e0; color: white; font-size: 0.7rem; line-height: 22px;
        text-align: center; margin-right: 6px; vertical-align: middle;
    }
    .step-item.active .step-num { background: #3182ce; }
    .step-item.done .step-num { background: #38a169; }
    .card {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 20px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
    .card-header {
        display: flex; align-items: center; gap: 8px; margin-bottom: 14px;
        padding-bottom: 10px; border-bottom: 1px solid #edf2f7;
    }
    .card-icon { font-size: 1.2rem; }
    .card-title { font-size: 0.95rem; font-weight: 600; color: #2d3748; margin: 0; }
    .card-subtitle { font-size: 0.75rem; color: #a0aec0; margin-left: auto; }
    .chapter-item {
        display: flex; align-items: center; padding: 10px 14px; background: #f7fafc;
        border: 1px solid #e2e8f0; border-radius: 8px; margin: 6px 0; transition: all 0.2s;
    }
    .chapter-item:hover { border-color: #90cdf4; background: #ebf8ff; }
    .chapter-icon {
        width: 32px; height: 32px; border-radius: 8px;
        background: linear-gradient(135deg, #667eea, #764ba2); color: white;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.8rem; font-weight: 600; margin-right: 12px; flex-shrink: 0;
    }
    .chapter-info { flex: 1; }
    .chapter-name { font-size: 0.88rem; font-weight: 500; color: #2d3748; }
    .chapter-meta { font-size: 0.72rem; color: #a0aec0; margin-top: 2px; }
    .stats-bar { display: flex; gap: 16px; margin: 12px 0; }
    .stat-item {
        flex: 1; background: #f7fafc; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 12px 16px; text-align: center;
    }
    .stat-value { font-size: 1.4rem; font-weight: 700; color: #2b6cb0; }
    .stat-label { font-size: 0.72rem; color: #a0aec0; margin-top: 2px; }
    .tag {
        display: inline-block; padding: 3px 10px; border-radius: 12px;
        font-size: 0.7rem; font-weight: 600;
    }
    .tag-blue { background: #ebf8ff; color: #2b6cb0; }
    .tag-green { background: #f0fff4; color: #276749; }
    .tag-yellow { background: #fffff0; color: #975a16; }
    .tag-red { background: #fff5f5; color: #c53030; }
    .tag-purple { background: #faf5ff; color: #6b46c1; }
    .empty-state { text-align: center; padding: 40px 20px; color: #a0aec0; }
    .empty-state .empty-icon { font-size: 2.5rem; margin-bottom: 12px; }
    .empty-state .empty-text { font-size: 0.9rem; margin-bottom: 4px; }
    .empty-state .empty-hint { font-size: 0.78rem; color: #cbd5e0; }
    .memory-panel {
        background: linear-gradient(135deg, #fffff0, #fefcbf);
        border: 1px solid #ecc94b; border-radius: 10px; padding: 16px; margin: 8px 0;
    }
    .memory-item { display: flex; gap: 8px; margin: 6px 0; font-size: 0.82rem; }
    .memory-item .memory-key { color: #975a16; font-weight: 600; white-space: nowrap; }
    .memory-item .memory-val { color: #744210; }
    .sidebar-group-title {
        font-size: 0.78rem; font-weight: 600; color: #4a5568;
        text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;
        display: flex; align-items: center; gap: 6px;
    }
    section[data-testid="stSidebar"] { background: #f8fafc; }
    .stButton > button { border-radius: 8px; font-weight: 500; font-size: 0.82rem; padding: 0.4rem 1rem; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: #f7fafc; padding: 4px; border-radius: 10px; border: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 8px 20px; font-size: 0.82rem; }
    .stTabs [aria-selected="true"] { background: white !important; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .restore-banner {
        background: linear-gradient(135deg, #f0fff4, #c6f6d5);
        border: 1px solid #68d391; border-radius: 10px; padding: 12px 16px;
        margin-bottom: 16px; display: flex; align-items: center; gap: 10px;
    }
    @media (max-width: 768px) {
        .header-bar { flex-direction: column; text-align: center; }
        .stats-bar { flex-direction: column; }
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 系统提示词
# ============================================================
SYSTEM_PROMPT = """【微短剧生成 3.1 系统指令】

═══════════════════════════════════════
第零法则：视觉翻译（一切规则之上的规则）
═══════════════════════════════════════

小说是给眼睛的——读者靠文字在脑中自己生成画面。
剧本是给画面的——观众只能看到或听到你拍给他看的东西。

你的工作是——把小说用文字"告诉"读者的一切，全部翻译成摄像机能拍到的画面,并用人物的台词（声音）来增加代入感！

禁止对角色OOC，人物的台词、行为、举止都必须符合小说里的人设！
因此在给核心角色编写每一句台词的时候都要参考【角色驱动卡】

═══════════════════════════════════════
翻译铁律
═══════════════════════════════════════

铁律一：小说的"叙述"必须翻译为"动作流"
铁律二：小说的"心理描写"必须翻译为"身体反应搭配角色内心独白"
铁律三：小说的"设定/背景交代"必须翻译为"环境展示"
铁律四：台词的正确用法——塑造起人物

═══════════════════════════════════════
台词的黄金法则
═══════════════════════════════════════

【核心原则：台词是角色性格的DNA标签，不是越短越好】

不同角色必须有截然不同的说话方式，这比"精简"重要一万倍。

举例——同样表达"危险，快走"：
· 暴躁军人："都他妈愣着干嘛？撤！现在！"
· 冷静医生："情况不对。我们需要立刻离开这里。"
· 怂包少年："哥、哥哥……那个……咱能不能……先……"
· 傲娇大小姐："谁要跟你们一起跑了。……哼，不过本小姐今天刚好也想换个地方。"
· 老练杀手：（一言不发，直接拽起对方就走）
· 话痨技术宅："等等等等，我算了一下，按它的速度和我们的距离，大概还有47秒——不对，43秒，快跑快跑快跑！"

长短取决于角色性格，不取决于"精简原则"。

【台词长短的真实规律】
→ 角色性格决定基础句长
→ 情绪类型决定变化方向：
  · 暴怒/恐惧/震惊 → 比平时更短（但话痨的"短"可能仍然比沉默角色的"长"要长）
  · 紧张/兴奋/炫耀 → 比平时更长更碎
  · 压抑/隐忍/心碎 → 说一半吞回去、词不达意、答非所问
→ 关系决定说话方式：同一角色面对不同人说话不同

【绝对禁止的台词方式】
❌ 把所有角色台词统一缩短到2-4个字——会让所有角色都像"高冷人设"
❌ 删掉角色口头禅、语气词——那是角色灵魂
❌ 把话痨改成惜字如金——那是OOC
❌ 台词和画面分开写——必须嵌入画面流中

═══════════════════════════════════════
★★★ 分镜格式铁律（最重要的格式规范）★★★
═══════════════════════════════════════

【铁律A：台词必须嵌入画面动作流中】

台词不是单独一行，台词必须出现在它被说出的那个精确时间位置上，
和此刻正在发生的动作、表情、身体状态写在一起。

❌ 绝对禁止的格式（台词与画面分离）：
```
画面：[秦洛打响指，电流在指尖炸开，许多多被吓得后弹]
秦洛："看，技能点。"
许多多OS：（他有异能？！）
音效：电流滋滋声
```
问题：读者/导演不知道"看，技能点"这句话是在打响指前说的？还是后弹之后说的？

✅ 正确格式（台词嵌入动作流的精确时间点）：
```
秦洛带着战术手套的手指伸进毯子边缘——
啪！响指。一簇幽蓝电流在指尖炸开（音效：尖锐滋滋声），
电光照亮整个角落。
秦洛（得意挑眉，嘴角歪向左边）："看。哥的技能点。"
许多多灰白的瞳孔骤然收缩——身体本能后弹，
后背撞在车厢壁上。
许多多一脸诧异，OS：（异能？！他……真的有异能？！）
```

规则：
1. 台词出现在它被说出的精确时间点——在哪个动作之后、哪个动作之前
2. 台词前面必须紧跟说话时的【情绪状态+面部表情+身体动作】
3. 内心OS出现在角色产生这个想法的精确时刻
4. 音效出现在发出声音的那个动作旁边，用（）标注

【铁律B：说台词时必须描写说话者的完整状态】

每一句台词前面，必须包含以下三要素中的至少两个：

① 情绪/语气标签：（低沉、暴怒、故作轻松、嘴硬但声音发颤、咬牙切齿……）
② 面部表情：（挑眉、眼神躲闪、下颌收紧、瞳孔放大、嘴角抽搐……）
③ 身体动作：（双手插兜、指尖点桌面、侧过头不看对方、攥紧拳头……）

❌ 禁止的写法（裸台词）：
秦洛："抱紧点。"

✅ 正确的写法：
秦洛低头看她，故意把表情板得很凶（但声音不自觉放软了）："抱紧点。掉下去被变异兽叼走，真就是一口一个小丧尸。"

✅ 更好的写法：
秦洛低头——本来想摆出教训小孩的凶脸，
但看到她灰白大眼睛滴溜溜乱转的样子，
喉结不自觉滚了一下，声音硬拽着往下压：
"抱紧点。掉下去被变异兽叼走，真就是一口一个小丧尸。"
他说完下意识把手臂往上紧了紧——
这个动作和他嘴里的威胁完全矛盾。
→ 观众同时看到：凶脸+放软的声音+收紧的手臂 = 嘴硬心软，全员心动。


【铁律D：好莱坞级动作奇观与镜头语法（视觉爆发力法则）】
当遇到射击、异能释放、巨兽袭击等战斗时刻，绝对禁止平铺直叙！
必须调用以下“高级镜头调度语法”，制造强烈的视觉冲击力：

1. 【子弹时间（Bullet Time）与微距跟踪】：
必须写出时间膨胀感。例如：慢动作特写子弹出膛，枪口震荡出扭曲的空气涟漪（空气阻力），镜头死死死贴着高速旋转的弹头（跟踪镜头），随后瞬间恢复正常语速，子弹狠狠掼入目标。
2. 【快慢速切（升降格）】：
动作极静与极动的瞬间切换。例如：上一秒是缓慢滴落的汗水或慢动作的后坐力震颤（升格），下一秒瞬间切为巨兽轰然倒塌的极速狂暴画面（降格/正常速）。
3. 【极速推镜（Crash Zoom）】：
瞬间拉近距离制造压迫感。例如：镜头从全景瞬间推至变异大象充满血丝的浑浊巨眼特写。
4. 【感官剥夺与音效反差】：
在最爆裂的动作前，先制造死寂。例如：枪响后，所有环境音瞬间消失，只剩尖锐的耳鸣声，随后再爆发巨兽砸地的震天轰鸣。

❌ 错误的干瘪描述：
白述开枪。子弹射中大象。大象倒下（2s）。

✅ 完美的动作奇观分镜示范（实算时长依然只要2-3秒）：
【镜头极速推近】特写白述扣下扳机的食指——砰！
【慢动作/子弹时间】枪口喷出炽热的火舌，巨大的后坐力震起他发梢的灰尘。一颗大口径穿甲弹撕裂夜风，弹头挤压空气形成一圈圈扭曲的水波纹阻力（1.5s）。
【镜头死死跟踪弹头】子弹在半空划出致命的红线，瞬间加速（快慢切）——噗嗤！精准绞碎变异巨象布满血丝的右眼！（1s）

【铁律F：真实三维物理与空间逻辑法则（反降智/反常识预警）】
AI经常因为追求“动作酷炫”而写出违背人体工学和物理常识的动作（例如：坐在越野车副驾驶的人，由于腿部空间受限，绝对不可能用脚直接踹回头顶的天窗！这属于毫无常识的低级漏洞）。

在编写任何动作前，必须在脑中运行【三维物理模拟器】：
1. 【空间与人体工学】：角色所处的空间有多大？姿势是什么？（狭窄车厢内无法挥舞长柄武器；坐姿无法向正上方高抬腿踹门；打开车顶天窗在真实情况中只能是用手砸/推）。
2. 【动线与发力逻辑】：动作必须符合真实的物理发力方式。
3. 【重力与惯性】：高速行驶的车辆上，人探出车外会被狂风吹得极难稳定，必须有明确的物理支撑点（如：一手死死抓住窗框边缘）。
4. 【道具溯源】：角色手里拿的道具、开枪的子弹，必须有明确的来源和合理的存放位置，严禁凭空变出物品。

🚨 强制指令：如果小说原著的描写本身违背了物理常识或逻辑漏洞，你必须在影视化翻译时，【自动将其修正】为符合真实物理逻辑的动作！绝对不允许照搬原著的降智设定！

【铁律G：反应镜头与“活体”法则（严禁角色道具化）】
AI常犯的致命错误：只描写正在说话或打斗的人，把旁边不说话、或者处于“被抱着/背着/牵着”的角色写成没有生命的“木头”或“背包”，导致角色看起来极度空洞、像个假人。
在影视剧中，只要角色在画面内，哪怕是背景板，哪怕不说话，也必须有属于角色性格的描述！

🚨 强制指令：
1. 【非说话者的反应镜头】：当A在长篇大论或激烈行动时，必须给画面内的B（尤其是核心角色）穿插0.5-1.5秒的【反应镜头】（微表情、翻白眼、手指抓紧、眼神躲闪或呼吸变化）。
2. 【被动状态的微细节】：如果角色处于“被抱着/拉着”的被动状态（如丧尸许多多），必须描写她/他的身体反馈和感官动作。
❌ 错误的空洞描写（像抱了个道具）：秦洛单臂托抱着许多多，大步流星走着。陈小飞跑过来说话。
✅ 正确的活体描写（鲜活感拉满）：秦洛单臂托抱着许多多往前走。许多多像无尾熊一样死死搂着他的脖子，灰蒙蒙的眼睛滴溜溜地四下乱转，听到陈小飞激动的声音时，她迟钝地歪了歪脑袋，咬了咬自己的手指（1.5s）。

═══════════════════════════════════════
灵魂锚定
═══════════════════════════════════════
你不是在"把小说改成剧本"。你是在替这些角色活一遍。
产品规格：每集分镜数量自由抉择 | 无第三人称旁白 | 集集强钩子。

═══════════════════════════════════════
五条创作铁律
═══════════════════════════════════════
①【人设即法律】角色的性格、说话方式、行为逻辑必须95%忠于原著。
②【外化】一切"想、觉得、心痛、暗爽"必须转化为可拍摄的具体画面。允许第一人称内心OS，严禁第三人称旁白。
③【伏笔】每一个重大转折之前，必须存在至少一个视觉/听觉微伏笔。
④【潜台词】角色嘴上说的话与真实意图之间必须存在缝隙。台词传递表面意思，身体泄露真相。
⑤【钩子铁律】前15秒必须制造具体的疑问或情绪冲击。每集结尾必须制造悬念。集内至少一次情绪急转。

═══════════════════════════════════════
角色驱动卡系统
═══════════════════════════════════════
为每个主要角色建立驱动卡，每次写台词/行为时必须调用：
· 核心人格（一句话定义）
· 说话DNA：句式习惯/口头禅/绝对不说的话/示范原句
· 行为DNA：愤怒/心软/恐惧/说谎/得意时的物理反应
· 红线（绝对不做的事）
· 关系动态

校验：每句台词→"遮住角色名能猜出是谁？"→不能→重写。

═══════════════════════════════════════
画面描写规律
═══════════════════════════════════════
→ 必须有一个"不寻常的具体细节"
→ 用声音锚定空间（沉默场景更需要微小声音来放大沉默）
→ 光源必须具体
→ 身体失控比表情形容词有力一万倍
→ 反差动作比直球动作有力

═══════════════════════════════════════
完整剧本格式示范
═══════════════════════════════════════
白天
秦洛带着战术手套的手指伸进毯子边缘——
啪！响指。一簇幽蓝电流在指尖炸开，
电光瞬间照亮整个角落（音效：尖锐滋滋声）。
秦洛得意地挑起左边眉毛，嘴角歪出一个欠揍的弧度：
"看。哥的技能点。生存手册上没这玩意儿吧？"
许多多灰白的瞳孔骤然收缩——
身体本能地向后一弹，后背撞在车厢铁壁上，
发出沉闷的一声响（音效：后背撞击闷响）。
她的手指不自觉攥紧了毯子边缘，指甲陷进绒毛里。
许多多OS：（异能……是真的存在的？
那他们能活到现在……就是靠这个？）

格式要点：
1. 台词嵌入在动作流的精确时间位置
2. 台词前紧跟说话者的表情+情绪+身体状态
3. 内心OS在角色产生想法的时刻出现
4. 音效用（）标注在发声的动作旁边

═══════════════════════════════════════
题材引擎
═══════════════════════════════════════
【需要观众爽】→ 弹簧法
【需要观众心动】→ 磁铁法
【需要观众虐】→ 错位法
【需要观众紧张】→ 橡皮筋法
【需要观众笑】→ 错位法

═══════════════════════════════════════
工作流
═══════════════════════════════════════
【第1轮：全局提炼】故事核心、角色驱动卡、大纲、核心节点、逻辑链、氛围基调、视觉强场景
【第2轮：开场手法设计】6条不同方案，含前30秒逐秒画面
【第3轮：剧本生成】编剧内心独白+结构速写+角色调用+影视化排雷+完整分镜
【第4轮：自检与优化】五个敌对视角+量化打分+细节清单"""

REVIEW_SYSTEM_PROMPT = """你是一个专业的微短剧分镜质检专家。对照小说原文，对每一条分镜进行严格的质量检查。

必须切换为以下五个敌对视角，逐一对整集发起攻击：

【视角1：普通观众（刷短视频的路人）】
- 哪里看不懂？哪里无聊想跳过？
- 我能不能在完全不知道原著的情况下看懂这一集？
- 结尾够不够让我点"下一集"？
- 输出：作为路人观众，我会在第X秒划走，因为______

【视角2：竞品编剧与逻辑警察（想找你毛病的同行）】
- 【常识与物理排雷】：哪个动作描写是毫无常识、违背物理定律或人体工学的？（例如坐着高抬腿踹天窗、狭窄空间挥舞大剑、重力环境下的反牛顿动作等低级错误）
- 哪些分镜是"偷懒"的？（用台词代替画面、用旁白交代信息）
- 哪些情绪转折是"硬拗"的？（缺少铺垫就突然转变）
- 整体节奏有没有拖沓或跳跃？
- 输出：如果我是竞品，我会狠狠嘲笑你第X分镜的______动作完全违背了物理常识，在现实拍摄中应该修改为______。

【视角3：原著粉（对人设极度敏感的读者）】
- 哪个角色被OOC了？具体哪句话/哪个行为违背原著？
- 哪些核心情节被改掉了？改得合不合理？
- 角色关系的化学反应够不够？
- 原著中最打动人的情感核心有没有被保留？
- 输出：作为原著粉，我最不能接受的是______，因为原著中______

【视角4：剪辑师（负责后期剪辑的技术人员）】
- 哪些分镜时长虚标？（标10秒但内容只够5秒，或标10秒但内容需要20秒）
- 哪些分镜之间缺少衔接点？（上一镜结尾画面和下一镜开头画面接不上）
- 哪些分镜的动作描写不够精确，导致我无法判断镜头怎么拍？
- 有没有分镜的画面信息过载（一个镜头里塞了太多东西）？
- 台词和画面的时间关系清楚吗？我能判断台词在哪个动作时说出吗？
- 输出：作为剪辑师，我剪不动的地方是______，因为______

【视角5：导演（对整体质量负责的决策者）】
- 这集的"记忆点"是什么？观众看完能记住的画面是什么？
- 情绪曲线画出来是什么形状？有没有平坦段？
- 演员拿到这个剧本，能不能直接演？还是会来问我"这里怎么演"？
- 整集的视觉风格统一吗？有没有某个分镜画风突变？
- 如果只能保留3个分镜，我保留哪3个？其余的有没有可以合并或删除的？
- 画面里的“不说话”或处于“被动（被抱/被牵/）”的角色，是否被忽略，没有给符合（剧情/性格）的（微表情/动作）和反应镜头？
- 输出：作为导演，我最想重拍的是分镜______，最满意的是分镜______

【重点检查项：台词三合一】
对每句台词检查：
- 嵌入位置：这句话在动作流的哪个时间点说出？读者能否判断？
- 说话状态：说这句话时人物的表情、情绪、身体动作是否描写了？
- 角色DNA：这句话符合角色的说话习惯吗？


对每条分镜逐一输出检查报告，最后给出整集汇总。
7分以下必须给出具体修改方案。"""

# ============================================================
# Session State
# ============================================================
def init_session_state():
    defaults = {
        "api_key": "", "api_base": "https://yunwu.ai/v1/",
        "model_id": "deepseek-chat", "custom_model": "",
        "chapters": {}, "chapter_order": [],
        "current_step": 0, "current_episode": 1,
        "global_analysis": "", "opening_designs": "",
        "episodes": {}, "review_results": {},
        "memory": {
            "storyline": "", "characters": "", "progress": "",
            "last_ending": "", "pending_foreshadow": "",
            "next_foreshadow": "", "emotion_track": ""
        },
        "messages": [], "chat_history": [],
        "mode": "默认", "selected_chapters_for_analysis": [],
        "review_model": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# 启动时尝试恢复数据
if not st.session_state.get("_restore_attempted"):
    st.session_state["_restore_attempted"] = True
    restored = auto_restore()
    if restored:
        st.session_state["_just_restored"] = True

# ============================================================
# API调用
# ============================================================
def get_active_model():
    model = st.session_state.model_id
    if model == "自定义模型":
        model = st.session_state.custom_model
    return model if model else "deepseek-chat"

def call_api_streaming(messages, system_prompt=SYSTEM_PROMPT):
    api_key = st.session_state.api_key
    api_base = st.session_state.api_base.rstrip("/")
    model = get_active_model()
    if not api_key:
        st.error("❌ 请先配置 API Key")
        return None
    if not api_base:
        st.error("❌ 请先配置接口地址")
        return None
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "stream": True, "temperature": 0.7, "max_tokens": 16384
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(f"{api_base}/chat/completions", headers=headers, json=data, stream=True, timeout=300)
            if resp.status_code == 429:
                wait_time = (attempt + 1) * 30
                st.warning(f"⚠️ API限流，{wait_time}秒后自动重试（第{attempt+1}/{max_retries}次）...")
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            return resp
        except requests.exceptions.Timeout:
            st.error("❌ 超时（300秒）")
            return None
        except requests.exceptions.ConnectionError:
            st.error("❌ 无法连接，检查接口地址")
            return None
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            if code == 429:
                wait_time = (attempt + 1) * 30
                st.warning(f"⚠️ API限流，{wait_time}秒后自动重试（第{attempt+1}/{max_retries}次）...")
                time.sleep(wait_time)
                continue
            body = ""
            try:
                body = e.response.text[:500] if e.response is not None else ""
            except:
                pass
            st.error(f"❌ HTTP {code}: {body}")
            return None
        except Exception as e:
            st.error(f"❌ {type(e).__name__}: {e}")
            return None
    st.error("❌ 多次重试仍被限流，请等待几分钟后再试")
    return None

def process_stream(response):
    if response is None:
        return
    try:
        for line in response.iter_lines():
            if not line:
                continue
            try:
                line_str = line.decode("utf-8")
            except:
                continue
            if not line_str.startswith("data: "):
                continue
            data_str = line_str[6:].strip()
            if data_str == "[DONE]":
                break
            if not data_str:
                continue
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices")
            if not choices or not isinstance(choices, list) or len(choices) == 0:
                continue
            first = choices[0]
            if not isinstance(first, dict):
                continue
            delta = first.get("delta")
            if not delta or not isinstance(delta, dict):
                continue
            content = delta.get("content")
            if content:
                yield content
    except requests.exceptions.ChunkedEncodingError:
        st.warning("⚠️ 传输中断，已保存内容")
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ 连接中断")
    except Exception as e:
        st.warning(f"⚠️ {type(e).__name__}: {e}")

def stream_to_container(response, container):
    if response is None:
        return ""
    full = ""
    for chunk in process_stream(response):
        full += chunk
        container.markdown(full)
    return full

def call_api_non_streaming(messages, system_prompt=SYSTEM_PROMPT):
    api_key = st.session_state.api_key
    api_base = st.session_state.api_base.rstrip("/")
    model = get_active_model()
    if not api_key or not api_base:
        return None
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "stream": False, "temperature": 0.7, "max_tokens": 16384
    }
    try:
        resp = requests.post(f"{api_base}/chat/completions", headers=headers, json=data, timeout=120)
        resp.raise_for_status()
        result = resp.json()
        choices = result.get("choices")
        if not choices or len(choices) == 0:
            return None
        return choices[0].get("message", {}).get("content", "")
    except Exception as e:
        st.error(f"❌ {type(e).__name__}: {e}")
        return None

# ============================================================
# 章节管理
# ============================================================
def add_chapter(name, content):
    if name and content:
        st.session_state.chapters[name] = content
        if name not in st.session_state.chapter_order:
            st.session_state.chapter_order.append(name)
        auto_save()
        return True
    return False

def remove_chapter(name):
    if name in st.session_state.chapters:
        del st.session_state.chapters[name]
        if name in st.session_state.chapter_order:
            st.session_state.chapter_order.remove(name)
        auto_save()

def get_combined_text(names=None):
    if names is None:
        names = st.session_state.chapter_order
    return "\n\n".join(f"【{n}】\n{st.session_state.chapters[n]}" for n in names if n in st.session_state.chapters)

# ============================================================
# 自动提取末尾分镜
# ============================================================
def extract_last_scenes(script, n=2):
    """从剧本中自动提取最后n个分镜"""
    scenes = re.split(r'(?=【分镜\s*\d+】)', script)
    scenes = [s.strip() for s in scenes if s.strip() and '【分镜' in s]
    if not scenes:
        return ""
    last_scenes = scenes[-n:]
    return "\n\n".join(last_scenes)

# ============================================================
# Prompt构建
# ============================================================
def build_analysis_prompt(text):
    return f"""【微短剧3.1启动】

以下是需要改编的小说原文：

{text}

请执行【第1轮：全局提炼】，输出：
1. 一句话故事核心
2. 每个主要角色的【驱动卡】（必须从原著提取原句作为说话DNA示范，特别注意每个角色的说话习惯差异）
3. 故事大纲（分阶段）+ 各阶段核心情绪类型
4. 必须保留的核心情节节点（10-20个）
5. 需要补充的逻辑链节点
6. 全剧环境/氛围基调 + 天气光影变化建议
7. 视觉强场景与短剧记忆点（5-8个瞬间，每个3-5句具体画面描述）"""

def build_opening_prompt():
    return """请执行【第2轮：开场手法设计】

输出6条完全不同的第1集开场方案，每条包含：
- 开场类型标签
- 前30秒逐秒画面描述
- 30秒后如何衔接主线"""

def build_episode_prompt(ep, text, opening="", prev_ending=""):
    mem = st.session_state.memory
    mem_str = ""
    if mem.get("storyline"):
        mem_str = f"""
📌 主线：{mem['storyline']}
📌 人物：{mem['characters']}
📌 进度：第{mem['progress']}集
📌 伏笔：{mem['pending_foreshadow']}
📌 引爆：{mem['next_foreshadow']}
📌 情绪：{mem['emotion_track']}"""

    prev_str = ""
    if prev_ending and prev_ending.strip():
        prev_str = f"""
═══════════════════════════════════════
🔗 上集末尾（必须衔接）
═══════════════════════════════════════
以下是上一集的结尾分镜，本集第一个分镜必须与之自然衔接：
- 画面衔接：本集开场画面必须接上上集最后的"衔接点"
- 情绪衔接：延续上集结尾的情绪氛围（可以延续也可以反转，但不能无视）
- 时空衔接：注意角色的物理位置、状态、穿着与上集保持一致
- 如果上集结尾有悬念钩子，本集需要在合适时机回应

上集末尾内容：
{prev_ending}
"""
    else:
        prev_str = "\n（本集为第一集或新篇章开始，无需衔接上集）\n"

    return f"""请执行【第3轮：剧本生成】—— 第{ep}集
{mem_str}
{prev_str}
{"选择的开场方案：" + opening if opening else ""}

参考小说原文：
{text}

严格执行前置ABCD，然后输出完整分镜剧本。

【分镜格式强制要求——必须严格遵守】

1. 台词必须嵌入画面动作流中，出现在它被说出的精确时间位置
   不允许把台词单独放在画面描写下面！

2. 每句台词前面必须紧跟说话者的：
   - 情绪/语气（低沉/暴怒/故作轻松/嘴硬但声音发颤……）
   - 面部表情（挑眉/眼神躲闪/下颌收紧/嘴角抽搐……）
   - 身体动作（双手插兜/侧过头/攥拳……）
   至少写两个。

3. 内心OS出现在角色产生想法的那个时刻

4. 音效用（）标注在发声动作旁边

5.遇到动作戏/危机爆发，必须写出专业镜头语句，并强制调用【好莱坞级镜头语法】：
   - 必须出现“特写”、“跟踪镜头”、“慢动作/子弹时间”、“极速推拉”等导演术语！
   - 必须描写空气扭曲、后坐力、弹道轨迹、巨兽体型压迫感等视觉奇观！
   - 你可以用100-200字去极致描绘一发子弹破空的空气阻力，即使这段描写的实算时长只有2-3秒。

6.动作生成前置排雷（物理与常识校验）：
   - 写每一个动作前，检查是否符合物理常识（副驾驶怎么踹天窗？手被绑在背后怎么开枪？）。
   - 发现原著有逻辑硬伤，必须自动用符合常识的合理动作替换，并在内心独白的【影视化排雷】中注明修改原因

7.严禁角色“道具化”发呆：
   - 画面中如果不说话的核心角色（特别是被抱着/牵引着的角色/站着背景的角色），绝对不能变成空洞的背景板！
   - 必须强制穿插他们的【反应镜头】（微表情/眼神乱转/小动作/身体反馈），赋予他们鲜活的生命感！

示范格式：
【分镜x】
[角色动作描写]——
[继续动作/变化]（音效：xxx）。
角色A（情绪描写+表情+身体状态）："台词内容"
[另一角色的反应动作]。
角色B（情绪描写+表情+身体状态） OS：（内心独白内容）"""

def build_review_prompt(ep, script, text):
    return f"""请对第{ep}集剧本执行完整的【第4轮：自检与优化】。

【小说原文】
{text}

【剧本分镜】
{script}

请严格按照以下内容逐一执行，不得遗漏任何部分：

【重点2：台词嵌入度】
每句台词是否嵌入在画面动作流的精确位置？
还是单独另起一行与画面分离？

【重点3：台词情绪描写】
每句台词前面是否描写了说话者当时的情绪+表情+身体状态？
还是"裸台词"（只有角色名+台词内容）？

【第二部分：五个敌对视角攻击】
质检完所有分镜后，切换为以下五个视角逐一攻击整集：

视角1——普通观众（刷短视频的路人）：
不看原著能看懂吗？有代入感吗？
→ 输出："我会在第X秒划走，因为______"

视角2——竞品编剧（找毛病的同行）：
哪些情节不连贯？哪些情绪硬拗？哪些台词不符合角色人设？
→ 输出："我会攻击你的______，并用______做得更好"

视角3——原著粉（人设敏感的读者）：
哪个角色OOC？核心情节被改了吗？主角戏份有变少吗？情感核心保留了吗？
→ 输出："最不能接受______，因为原著中______"

视角4——剪辑师（后期技术人员）：
时长虚标？缺衔接点？动作不够精确？画面信息过载？台词时间关系清楚吗？
→ 输出："剪不动的地方是______，因为______"

视角5——导演（整体质量负责人）：
记忆点是什么？情绪曲线形状？演员能直接演吗？视觉风格统一吗？
→ 输出："最想重拍分镜______，最满意分镜______"

输出检查报告+汇总。7分以下必须给修改方案。"""

def build_dialogue_optimization_prompt(ep, script, global_analysis=""):
    character_info = ""
    if global_analysis:
        character_info = f"\n【角色驱动卡参考】\n{global_analysis[:4000]}\n"
    return f"""台词优化第{ep}集。

{character_info}

【核心：台词优化≠精简！而是个性化+潜台词化+情绪匹配】

优化步骤：
1. 确认每个角色的说话DNA
2. 逐句检查：个性标签、情绪匹配、潜台词深度、关系动态
3. 补充台词前的情绪/表情/身体描写（如果缺失）
4. 确保台词嵌入在画面动作流的正确时间位置

❌ 禁止：统一缩短/删口头禅/让话痨变沉默/台词与画面分离
✅ 要求：每处修改标注原因+关联角色DNA

当前剧本：
{script}

输出优化后完整剧本。"""

def build_visual_optimization_prompt(ep, script):
    return f"""画面优化第{ep}集。

要求：
1. 不寻常具体细节（声音/光影/微动作）
2. 声音锚定空间
3. 光源具体化
4. 身体失控＞表情形容词
5. 反差动作＞直球动作
6. 每分镜≥5个动作事件（有时间流动感）
7. 台词保持嵌入式格式不变
8. 实算时长不变

当前剧本：
{script}

输出优化后完整剧本，修改处标注【🎨】。"""

def build_emotion_optimization_prompt(ep, script):
    return f"""情绪优化第{ep}集。

要求：
1. 开场15秒足够冲击
2. 集内至少一次情绪急转
3. 结尾悬念钩子
4. 情绪曲线有起伏
5. 题材引擎（弹簧法/磁铁法/错位法/橡皮筋法）
6. ≥65%转折来自互动
7. 台词格式和嵌入方式不变

当前剧本：
{script}

输出优化后完整剧本，修改处标注【❤️】。"""

# ============================================================
# 侧边栏
# ============================================================
with st.sidebar:
    st.markdown('<div class="sidebar-group-title">🔌 API 配置</div>', unsafe_allow_html=True)
    api_base = st.text_input("接口地址", value=st.session_state.api_base, key="sb_ab", placeholder="https://yunwu.ai/v1/")
    st.session_state.api_base = api_base
    api_key = st.text_input("API Key", value=st.session_state.api_key, type="password", key="sb_ak", placeholder="sk-...")
    st.session_state.api_key = api_key

    st.markdown("---")
    st.markdown('<div class="sidebar-group-title">🤖 模型</div>', unsafe_allow_html=True)
    model_options = [
        "deepseek-chat", "deepseek-reasoner",
        "claude-sonnet-4-20250514", "claude-opus-4-20250514",
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini",
        "gemini-2.5-pro-preview-06-05", "自定义模型"
    ]
    cm1, cm2 = st.columns([3, 1])
    with cm1:
        sel = st.selectbox("生成模型", model_options,
            index=model_options.index(st.session_state.model_id) if st.session_state.model_id in model_options else 0, key="sb_m")
        st.session_state.model_id = sel
    with cm2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔗", key="sb_t", use_container_width=True, help="测试"):
            with st.spinner("..."):
                r = call_api_non_streaming([{"role": "user", "content": "回复OK"}], "你是助手。")
                st.success("✅") if r else st.error("❌")
    if sel == "自定义模型":
        cm = st.text_input("模型ID", value=st.session_state.custom_model, key="sb_c", placeholder="deepseek-v3")
        st.session_state.custom_model = cm
    rev_opts = ["与生成模型相同"] + model_options
    rv = st.selectbox("质检模型", rev_opts, key="sb_rv")
    st.session_state.review_model = None if rv == "与生成模型相同" else rv

    st.markdown("---")
    st.markdown('<div class="sidebar-group-title">🎯 模式</div>', unsafe_allow_html=True)
    md = st.radio("", ["📋 默认", "⚡ 快速"], key="sb_md", label_visibility="collapsed")
    st.session_state.mode = "默认" if "默认" in md else "快速"

    st.markdown("---")
    st.markdown('<div class="sidebar-group-title">💾 数据</div>', unsafe_allow_html=True)
    if st.button("📌 全局记忆", use_container_width=True, key="sb_me"):
        st.session_state["show_memory_modal"] = True
    if st.session_state.episodes:
        st.download_button("📦 导出全部", use_container_width=True, key="sb_ex",
            data=json.dumps({"analysis": st.session_state.global_analysis,
                "episodes": {str(k): v for k, v in st.session_state.episodes.items()},
                "reviews": {str(k): v for k, v in st.session_state.review_results.items()},
                "memory": st.session_state.memory}, ensure_ascii=False, indent=2),
            file_name=f"剧本_{datetime.now().strftime('%m%d_%H%M')}.json", mime="application/json")

    # 手动保存按钮
    if st.button("💾 手动保存", use_container_width=True, key="sb_sv"):
        auto_save()
        st.success("✅ 已保存到本地")

    # 安全重置（二次确认）
    if st.button("🗑️ 重置", use_container_width=True, key="sb_rs"):
        if st.session_state.get("confirm_reset"):
            data_keys = ["chapters", "chapter_order", "current_step", "current_episode",
                         "global_analysis", "opening_designs", "episodes", "review_results",
                         "memory", "messages", "chat_history", "mode",
                         "selected_chapters_for_analysis", "confirm_reset",
                         "_restore_attempted", "_just_restored"]
            for k in data_keys:
                if k in st.session_state:
                    del st.session_state[k]
            clear_autosave()
            init_session_state()
            st.rerun()
        else:
            st.session_state["confirm_reset"] = True
            st.warning("⚠️ 再次点击确认重置（所有数据将清除）")
            st.rerun()

# ============================================================
# 顶部
# ============================================================

# 数据恢复提示
if st.session_state.get("_just_restored"):
    st.markdown("""<div class="restore-banner">
    <span style="font-size:1.2rem;">🔄</span>
    <span style="font-size:0.85rem;color:#276749;"><b>数据已自动恢复</b> — 检测到上次的工作数据，已自动载入。</span>
    </div>""", unsafe_allow_html=True)
    st.session_state["_just_restored"] = False

step_names = ["导入章节", "全局提炼", "开场设计", "生成剧本", "质检优化"]
current = st.session_state.current_step
st.markdown(f"""<div class="header-bar"><div class="header-left">
<div class="header-title">🎬 影视化视觉翻译引擎 V3.2</div>
<div class="header-sub">视觉翻译法则 · 角色DNA台词 · 台词嵌入画面流 · 实算时长</div></div>
<div style="display:flex;gap:8px;flex-wrap:wrap;">
<span class="header-badge">📚 {len(st.session_state.chapter_order)}章</span>
<span class="header-badge">🎬 {len(st.session_state.episodes)}集</span>
<span class="header-badge">🤖 {get_active_model()}</span></div></div>""", unsafe_allow_html=True)

sh = ""
for i, n in enumerate(step_names):
    c = "done" if i < current else ("active" if i == current else "")
    ic = "✓" if i < current else str(i + 1)
    sh += f'<div class="step-item {c}"><span class="step-num">{ic}</span>{n}</div>'
st.markdown(f'<div class="step-indicator">{sh}</div>', unsafe_allow_html=True)

if st.session_state.get("show_memory_modal"):
    mem = st.session_state.memory
    with st.expander("📌 全局记忆", expanded=True):
        st.markdown(f"""<div class="memory-panel">
<div class="memory-item"><span class="memory-key">📌 主线：</span><span class="memory-val">{mem.get('storyline') or '—'}</span></div>
<div class="memory-item"><span class="memory-key">👥 人物：</span><span class="memory-val">{mem.get('characters') or '—'}</span></div>
<div class="memory-item"><span class="memory-key">📍 进度：</span><span class="memory-val">{mem.get('progress') or '—'}</span></div>
<div class="memory-item"><span class="memory-key">🔚 结尾：</span><span class="memory-val">{mem.get('last_ending') or '—'}</span></div>
<div class="memory-item"><span class="memory-key">🔮 伏笔：</span><span class="memory-val">{mem.get('pending_foreshadow') or '—'}</span></div>
<div class="memory-item"><span class="memory-key">💥 引爆：</span><span class="memory-val">{mem.get('next_foreshadow') or '—'}</span></div>
<div class="memory-item"><span class="memory-key">❤️ 情绪：</span><span class="memory-val">{mem.get('emotion_track') or '—'}</span></div>
</div>""", unsafe_allow_html=True)
        if st.button("关闭", key="cmm"):
            st.session_state["show_memory_modal"] = False
            st.rerun()

# ============================================================
# 步骤一
# ============================================================
st.markdown("""<div class="card"><div class="card-header">
<span class="card-icon">📖</span><span class="card-title">步骤一：导入小说章节</span>
<span class="card-subtitle">.txt/.md 上传 或 粘贴</span></div></div>""", unsafe_allow_html=True)

ca, cl = st.columns([1, 1])
with ca:
    at = st.tabs(["📁 上传", "✍️ 粘贴"])
    with at[0]:
        up = st.file_uploader("选择", type=["txt", "md", "text"], accept_multiple_files=True, key="up")
        if up:
            for u in up:
                if u.size > 200 * 1024:
                    st.warning(f"⚠️ {u.name}>200KB")
                    continue
                try:
                    ct = u.read().decode("utf-8", errors="ignore")
                except:
                    ct = ""
                cn = u.name.rsplit(".", 1)[0] if "." in u.name else u.name
                if cn not in st.session_state.chapters and ct:
                    add_chapter(cn, ct)
                    st.success(f"✅ {cn} ({len(ct)}字)")
    with at[1]:
        pn = st.text_input("名称", placeholder="第1章", key="pn")
        pc = st.text_area("内容", height=180, placeholder="粘贴...", key="pc")
        if st.button("➕ 添加", key="pa", use_container_width=True, type="primary"):
            if pn and pc:
                add_chapter(pn, pc)
                st.success(f"✅ {pn}")
                st.rerun()
            else:
                st.warning("请填写")

with cl:
    st.markdown("**已导入**")
    if st.session_state.chapter_order:
        tc = sum(len(st.session_state.chapters.get(c, "")) for c in st.session_state.chapter_order)
        st.markdown(f"""<div class="stats-bar">
<div class="stat-item"><div class="stat-value">{len(st.session_state.chapter_order)}</div><div class="stat-label">章节</div></div>
<div class="stat-item"><div class="stat-value">{tc:,}</div><div class="stat-label">总字</div></div>
<div class="stat-item"><div class="stat-value">{tc // max(len(st.session_state.chapter_order), 1):,}</div><div class="stat-label">均字</div></div>
</div>""", unsafe_allow_html=True)
        for i, ch in enumerate(st.session_state.chapter_order):
            ct = st.session_state.chapters.get(ch, "")
            c1, c2, c3 = st.columns([5, 1, 1])
            with c1:
                st.markdown(f"""<div class="chapter-item"><div class="chapter-icon">{i + 1}</div>
<div class="chapter-info"><div class="chapter-name">{ch}</div><div class="chapter-meta">{len(ct):,}字</div></div></div>""", unsafe_allow_html=True)
            with c2:
                if st.button("👁️", key=f"v{i}", help="看"):
                    st.session_state[f"e{i}"] = not st.session_state.get(f"e{i}", False)
            with c3:
                if st.button("🗑️", key=f"d{i}", help="删"):
                    remove_chapter(ch)
                    st.rerun()
            if st.session_state.get(f"e{i}"):
                with st.expander(f"📖 {ch}", expanded=True):
                    st.text_area("", ct, height=200, disabled=True, key=f"p{i}")
    else:
        st.markdown("""<div class="empty-state"><div class="empty-icon">📚</div><div class="empty-text">暂无</div></div>""", unsafe_allow_html=True)

# ============================================================
# 步骤二
# ============================================================
st.markdown("""<div class="card"><div class="card-header">
<span class="card-icon">🔍</span><span class="card-title">步骤二：全局提炼</span>
<span class="card-subtitle">角色驱动卡 · 情节 · 视觉</span></div></div>""", unsafe_allow_html=True)

s2a, s2b = st.columns([1, 1])
with s2a:
    if st.session_state.chapter_order:
        sc = st.multiselect("选择章节", st.session_state.chapter_order, default=st.session_state.chapter_order, key="sc", label_visibility="collapsed")
        st.session_state.selected_chapters_for_analysis = sc
        if sc:
            st.info(f"📊 {len(sc)}章 · {sum(len(st.session_state.chapters.get(c, '')) for c in sc):,}字")
        b1, b2 = st.columns(2)
        with b1:
            da = st.button("🚀 提炼", key="da", use_container_width=True, type="primary", disabled=not (sc and st.session_state.api_key))
        with b2:
            if st.session_state.global_analysis:
                if st.button("🔄 重做", key="rd", use_container_width=True):
                    st.session_state.global_analysis = ""
                    st.rerun()
    else:
        st.info("💡 先导入")
        da = False

with s2b:
    st.markdown("**结果**")
    if da:
        t = get_combined_text(sc)
        ms = [{"role": "user", "content": build_analysis_prompt(t)}]
        with st.spinner("🧠 分析中..."):
            r = call_api_streaming(ms)
            if r:
                co = st.empty()
                f = stream_to_container(r, co)
                if f:
                    st.session_state.global_analysis = f
                    st.session_state.messages = ms + [{"role": "assistant", "content": f}]
                    st.session_state.current_step = max(st.session_state.current_step, 1)
                    auto_save()
                    st.success("✅ 完成！")
    elif st.session_state.global_analysis:
        with st.expander("📋 查看", expanded=False):
            st.markdown(st.session_state.global_analysis)
        st.markdown('<span class="tag tag-green">✅ 完成</span>', unsafe_allow_html=True)
    else:
        st.markdown("""<div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-text">等待</div></div>""", unsafe_allow_html=True)

# ============================================================
# 步骤三
# ============================================================
st.markdown("""<div class="card"><div class="card-header">
<span class="card-icon">🎬</span><span class="card-title">步骤三：编剧控制台</span>
<span class="card-subtitle">开场→生成→质检→优化</span></div></div>""", unsafe_allow_html=True)

t1, t2, t3 = st.columns([1, 2, 3])
with t1:
    en = st.number_input("集", 1, 200, st.session_state.current_episode, key="ei")
    st.session_state.current_episode = en
with t2:
    ec = st.multiselect("章节", st.session_state.chapter_order, key="ec", help="本集参考")
with t3:
    ad = bool(st.session_state.global_analysis)
    st.markdown(f"""<div style="display:flex;gap:8px;padding-top:24px;flex-wrap:wrap;">
<span class="tag tag-blue">第{en}集</span><span class="tag tag-purple">{get_active_model()}</span>
{"<span class='tag tag-green'>✅提炼</span>" if ad else "<span class='tag tag-yellow'>⚠️未提炼</span>"}</div>""", unsafe_allow_html=True)

# ============================================================
# 上集衔接区域
# ============================================================
with st.expander("🔗 上集衔接（可选）", expanded=False):
    auto_ending = st.session_state.memory.get("last_ending", "")
    if auto_ending:
        st.info(f"✅ 已自动提取第{st.session_state.memory.get('progress', '?')}集末尾分镜")

    prev_ending = st.text_area(
        "上集末尾内容（最后1-3个分镜）",
        value=auto_ending,
        height=150,
        key="prev_ending_input",
        help="粘贴上一集最后的分镜内容，AI会据此衔接。留空=第一集或新篇章开始",
        placeholder="留空表示不需要衔接（第一集或新篇章）\n\n或粘贴上一集最后的分镜内容，例如：\n【分镜11】（实算12.5s）\n场景：衣柜内外 · 傍晚...\n秦洛（咬牙切齿）：\"啧！你一个丧尸卖什么萌啊？\"\n..."
    )

    if st.button("🗑️ 清空衔接", key="clear_prev", help="清空表示新篇章开始"):
        st.session_state.memory["last_ending"] = ""
        auto_save()
        st.rerun()

# ============================================================
# 功能按钮
# ============================================================
bc = st.columns(7)
bd = [("🎯", "设计开场"), ("🎬", "生成剧本"), ("🔍", "质量检查"), ("💬", "优化台词"), ("🎨", "优化画面"), ("❤️", "优化情绪"), ("📦", "批量生成")]
bt = {}
for i, (ic, lb) in enumerate(bd):
    with bc[i]:
        bt[lb] = st.button(f"{ic} {lb}", key=f"b_{lb}", use_container_width=True, type="primary" if lb == "生成剧本" else "secondary")

# ============================================================
# 主Tabs
# ============================================================
mt = st.tabs(["📝 剧本", "🔍 质检", "🎯 开场", "💬 对话", "📊 总览"])

with mt[0]:
    if bt["设计开场"]:
        if not ad:
            st.warning("⚠️ 先提炼")
        else:
            ms = st.session_state.messages + [{"role": "user", "content": build_opening_prompt()}]
            with st.spinner("🎯..."):
                r = call_api_streaming(ms)
                if r:
                    co = st.empty()
                    f = stream_to_container(r, co)
                    if f:
                        st.session_state.opening_designs = f
                        st.session_state.messages = ms + [{"role": "assistant", "content": f}]
                        st.session_state.current_step = max(st.session_state.current_step, 2)
                        auto_save()
                        st.success("✅")

    if bt["生成剧本"]:
        if not ad:
            st.warning("⚠️ 先提炼")
        else:
            tx = get_combined_text(ec if ec else None)
            op = st.session_state.get("selected_opening", "")
            pe = prev_ending if prev_ending else ""
            pr = build_episode_prompt(en, tx, op, pe)
            cx = st.session_state.messages + [{"role": "user", "content": pr}]
            with st.spinner(f"🎬 第{en}集..."):
                r = call_api_streaming(cx)
                if r:
                    co = st.empty()
                    f = stream_to_container(r, co)
                    if f:
                        st.session_state.episodes[en] = f
                        st.session_state.messages = cx + [{"role": "assistant", "content": f}]
                        st.session_state.current_step = max(st.session_state.current_step, 3)
                        st.session_state.memory["progress"] = str(en)
                        last_scenes = extract_last_scenes(f, n=2)
                        if last_scenes:
                            st.session_state.memory["last_ending"] = last_scenes
                        auto_save()
                        st.success(f"✅ 第{en}集完成！")
                    else:
                        st.warning("⚠️ 空")

    if bt["批量生成"]:
        if not ad:
            st.warning("⚠️")
        else:
            b1, b2 = st.columns(2)
            with b1:
                bs = st.number_input("起始", 1, 200, en, key="bs")
            with b2:
                be = st.number_input("结束", 1, 200, min(en + 2, 200), key="be")
            if st.button("🚀 开始", key="bg", type="primary"):
                tx = get_combined_text(ec if ec else None)
                for e in range(int(bs), int(be) + 1):
                    st.markdown(f"---\n### 🎬 第{e}集")
                    pe = st.session_state.memory.get("last_ending", "")
                    cx = st.session_state.messages + [{"role": "user", "content": build_episode_prompt(e, tx, prev_ending=pe)}]
                    r = call_api_streaming(cx)
                    if r:
                        co = st.empty()
                        f = stream_to_container(r, co)
                        if f:
                            st.session_state.episodes[e] = f
                            st.session_state.messages = cx + [{"role": "assistant", "content": f}]
                            st.session_state.memory["progress"] = str(e)
                            last_scenes = extract_last_scenes(f, n=2)
                            if last_scenes:
                                st.session_state.memory["last_ending"] = last_scenes
                            auto_save()
                            st.success(f"✅ 第{e}集")
                        else:
                            st.warning(f"⚠️ 第{e}集空")
                            break
                    else:
                        st.error(f"❌ 第{e}集失败")
                        break

    if bt["优化台词"]:
        if en in st.session_state.episodes:
            pr = build_dialogue_optimization_prompt(en, st.session_state.episodes[en], st.session_state.global_analysis)
            ms = st.session_state.messages + [{"role": "user", "content": pr}]
            with st.spinner("💬 角色DNA台词优化..."):
                r = call_api_streaming(ms)
                if r:
                    co = st.empty()
                    f = stream_to_container(r, co)
                    if f:
                        st.session_state.episodes[en] = f
                        st.session_state.messages = ms + [{"role": "assistant", "content": f}]
                        last_scenes = extract_last_scenes(f, n=2)
                        if last_scenes:
                            st.session_state.memory["last_ending"] = last_scenes
                        auto_save()
                        st.success("✅ 台词优化完成（角色DNA驱动）")
        else:
            st.warning(f"⚠️ 第{en}集未生成")

    if bt["优化画面"]:
        if en in st.session_state.episodes:
            pr = build_visual_optimization_prompt(en, st.session_state.episodes[en])
            ms = st.session_state.messages + [{"role": "user", "content": pr}]
            with st.spinner("🎨..."):
                r = call_api_streaming(ms)
                if r:
                    co = st.empty()
                    f = stream_to_container(r, co)
                    if f:
                        st.session_state.episodes[en] = f
                        st.session_state.messages = ms + [{"role": "assistant", "content": f}]
                        last_scenes = extract_last_scenes(f, n=2)
                        if last_scenes:
                            st.session_state.memory["last_ending"] = last_scenes
                        auto_save()
                        st.success("✅ 画面优化完成")
        else:
            st.warning(f"⚠️ 第{en}集未生成")

    if bt["优化情绪"]:
        if en in st.session_state.episodes:
            pr = build_emotion_optimization_prompt(en, st.session_state.episodes[en])
            ms = st.session_state.messages + [{"role": "user", "content": pr}]
            with st.spinner("❤️..."):
                r = call_api_streaming(ms)
                if r:
                    co = st.empty()
                    f = stream_to_container(r, co)
                    if f:
                        st.session_state.episodes[en] = f
                        st.session_state.messages = ms + [{"role": "assistant", "content": f}]
                        last_scenes = extract_last_scenes(f, n=2)
                        if last_scenes:
                            st.session_state.memory["last_ending"] = last_scenes
                        auto_save()
                        st.success("✅ 情绪优化完成")
        else:
            st.warning(f"⚠️ 第{en}集未生成")

    st.markdown("---")
    if st.session_state.episodes:
        st.markdown("### 📜 已生成剧本")
        se = sorted(st.session_state.episodes.keys())
        et = st.tabs([f"第{e}集" for e in se])
        for ix, e in enumerate(se):
            with et[ix]:
                s = st.session_state.episodes[e]
                sh = len(re.findall(r'【分镜\s*\d+】', s))
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("分镜", sh or "—")
                m2.metric("时长", f"~{sh * 12}s" if sh else "—")
                m3.metric("字数", f"{len(s):,}")
                m4.metric("质检", "✅" if e in st.session_state.review_results else "⏳")
                st.markdown(s)
                d1, d2 = st.columns(2)
                with d1:
                    st.download_button(f"📥 导出", s, f"第{e}集.md", "text/markdown", key=f"dl{e}")
                with d2:
                    st.download_button("📋 纯文本", s, f"第{e}集_纯文本.txt", "text/plain", key=f"cd{e}")
    else:
        st.markdown("""<div class="empty-state"><div class="empty-icon">🎬</div><div class="empty-text">尚未生成</div></div>""", unsafe_allow_html=True)

with mt[1]:
    if bt["质量检查"]:
        if en not in st.session_state.episodes:
            st.warning(f"⚠️ 第{en}集未生成")
        else:
            tx = get_combined_text(ec if ec else None)
            sc_text = st.session_state.episodes[en]
            rm = [{"role": "user", "content": build_review_prompt(en, sc_text, tx)}]
            og = st.session_state.model_id
            if st.session_state.review_model:
                st.session_state.model_id = st.session_state.review_model
            with st.spinner(f"🔍 质检第{en}集..."):
                r = call_api_streaming(rm, REVIEW_SYSTEM_PROMPT)
                if r:
                    co = st.empty()
                    f = stream_to_container(r, co)
                    if f:
                        st.session_state.review_results[en] = f
                        st.session_state.current_step = max(st.session_state.current_step, 4)
                        auto_save()
                        st.success(f"✅ 第{en}集质检完成")
            st.session_state.model_id = og

    if st.session_state.review_results:
        for e in sorted(st.session_state.review_results.keys()):
            rv = st.session_state.review_results[e]
            with st.expander(f"📊 第{e}集", expanded=(e == en)):
                st.markdown(rv)
                f1, f2, f3 = st.columns(3)
                with f1:
                    if st.button(f"🔧 自动修改", key=f"fx{e}", type="primary"):
                        fp = f"""根据质检修改第{e}集所有7分以下项。

【修改格式要求】
1. 台词必须嵌入画面动作流（不能单独分行）
2. 每句台词前必须有情绪+表情+身体描写
3. 时长必须实算
4. 台词个性化（不能统一精简）

质检：\n{rv}\n原剧本：\n{st.session_state.episodes[e]}\n输出修改后完整剧本。"""
                        fm = st.session_state.messages + [{"role": "user", "content": fp}]
                        with st.spinner("🔧..."):
                            r = call_api_streaming(fm)
                            if r:
                                co = st.empty()
                                f = stream_to_container(r, co)
                                if f:
                                    # --- 新增：纯净版剧本提取器 ---
                                    # 防止AI输出的“【编剧内心独白】”等前言污染最终剧本
                                    final_script = f
                                    match = re.search(r'【分镜\s*1?】', f) # 寻找第一个分镜的开头
                                    if match:
                                        final_script = f[match.start():].strip() # 只截取分镜及之后的内容
                                    
                                    # 更新剧本内容为纯净版
                                    st.session_state.episodes[e] = final_script
                                    
                                    # 更新记忆库的末尾分镜
                                    last_scenes = extract_last_scenes(final_script, n=2)
                                    if last_scenes:
                                        st.session_state.memory["last_ending"] = last_scenes
                                        
                                    # --- 新增：强制UI刷新 ---
                                    st.success(f"✅ 第{e}集修改已自动保存！正在刷新剧本界面...")
                                    time.sleep(1.5) # 停顿1.5秒让用户看清提示
                                    st.rerun() # 强制刷新整个网页，同步更新“剧本”Tab
                with f2:
                    st.download_button("📥", rv, f"第{e}集_质检.md", "text/markdown", key=f"dr{e}")
                with f3:
                    if st.button("🔄 重检", key=f"rr{e}"):
                        if e in st.session_state.review_results:
                            del st.session_state.review_results[e]
                        st.rerun()
    else:
        st.markdown("""<div class="empty-state"><div class="empty-icon">🔍</div><div class="empty-text">暂无质检</div></div>""", unsafe_allow_html=True)

with mt[2]:
    if st.session_state.opening_designs:
        st.markdown("### 🎯 6套方案")
        st.markdown(st.session_state.opening_designs)
        st.markdown("---")
        o1, o2 = st.columns([3, 1])
        with o1:
            ch = st.text_input("选择", placeholder="1-6或自定义", key="oc")
        with o2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅", key="cf", use_container_width=True, type="primary"):
                if ch:
                    st.session_state["selected_opening"] = ch
                    auto_save()
                    st.success(f"✅ {ch}")
    else:
        st.markdown("""<div class="empty-state"><div class="empty-icon">🎯</div><div class="empty-text">待设计</div></div>""", unsafe_allow_html=True)

with mt[3]:
    st.markdown("### 💬 自由对话")
    for mg in st.session_state.chat_history[-20:]:
        with st.chat_message(mg["role"]):
            st.markdown(mg["content"])
    ui = st.chat_input("输入...", key="ci")
    if ui:
        st.session_state.chat_history.append({"role": "user", "content": ui})
        cx = ""
        if st.session_state.global_analysis:
            cx += f"\n【提炼】{st.session_state.global_analysis[:3000]}"
        if st.session_state.episodes:
            la = max(st.session_state.episodes.keys())
            cx += f"\n【第{la}集】{st.session_state.episodes[la][:2000]}"
        fm = f"背景：{cx}\n\n指令：{ui}" if cx else ui
        with st.chat_message("assistant"):
            r = call_api_streaming([{"role": "user", "content": fm}])
            if r:
                co = st.empty()
                f = stream_to_container(r, co)
                if f:
                    st.session_state.chat_history.append({"role": "assistant", "content": f})
                    auto_save()

with mt[4]:
    st.markdown("### 📊 总览")
    o1, o2, o3, o4 = st.columns(4)
    o1.metric("📚", len(st.session_state.chapter_order))
    o2.metric("🎬", len(st.session_state.episodes))
    o3.metric("✅", len(st.session_state.review_results))
    o4.metric("📝", f"{sum(len(v) for v in st.session_state.episodes.values()):,}" if st.session_state.episodes else "0")
    st.markdown("---")
    if st.session_state.episodes:
        for e in sorted(st.session_state.episodes.keys()):
            s = st.session_state.episodes[e]
            sh = len(re.findall(r'【分镜\s*\d+】', s))
            st.markdown(f"""<div class="chapter-item"><div class="chapter-icon" style="background:linear-gradient(135deg,#3182ce,#2b6cb0);">{e}</div>
<div class="chapter-info"><div class="chapter-name">第{e}集 <span class="tag tag-blue">{sh}镜</span> <span class="tag tag-green">~{sh * 12}s</span></div>
<div class="chapter-meta">{len(s):,}字 · {"✅" if e in st.session_state.review_results else "⏳"}</div></div></div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("#### 📌 记忆（可编辑）")
    for lb, ky in [("主线", "storyline"), ("人物", "characters"), ("进度", "progress"), ("结尾", "last_ending"), ("伏笔", "pending_foreshadow"), ("引爆", "next_foreshadow"), ("情绪", "emotion_track")]:
        nv = st.text_input(f"📌 {lb}", value=st.session_state.memory.get(ky, ""), key=f"m_{ky}")
        st.session_state.memory[ky] = nv

st.markdown("---")
st.markdown(f"""<div style="text-align:center;padding:16px 0;"><span style="color:#a0aec0;font-size:0.75rem;">
🎬 影视化视觉翻译引擎 V3.2 · 台词嵌入画面流 · 实算时长 · 角色DNA · {get_active_model()}</span></div>""", unsafe_allow_html=True)
