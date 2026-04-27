"""
心理咨询智能体
处理：心理压力疏导、情绪调节建议、心理咨询预约信息、心理健康知识
"""

from typing import Dict, Optional, AsyncGenerator
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_deepseek import ChatDeepSeek
from .base_agent import BaseAgent, AgentResponse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env_utils import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from rag_service import RAGService


# ============ 工具函数定义 ============

@tool
def self_assessment_guide(issue_type: str) -> str:
    """
    提供心理自评指导
    
    Args:
        issue_type: 问题类型（焦虑/抑郁/压力/睡眠/人际）
    """
    guides = {
        "焦虑": """
【焦虑情绪自评参考】

常见表现：
- 过度担心未来，难以控制的紧张感
- 身体反应：心跳加速、手心出汗、肌肉紧绷
- 注意力难以集中，易烦躁

日常调节建议：
1. 深呼吸练习：吸气4秒 → 屏息4秒 → 呼气6秒，重复5次
2. 正念冥想：每天10分钟，专注当下感受
3. 规律运动：每周3次有氧运动，每次30分钟
4. 减少咖啡因和酒精摄入

📌 如症状持续超过2周且影响日常生活，建议预约心理咨询。
        """,
        "抑郁": """
【抑郁情绪自评参考】

常见表现：
- 持续情绪低落，对事物失去兴趣
- 疲劳感明显，精力下降
- 睡眠问题（失眠或嗜睡）
- 自我评价过低，内疚感

日常调节建议：
1. 保持规律作息，固定起床和入睡时间
2. 从小事做起，设定可达成的小目标
3. 多晒太阳，增加户外活动时间
4. 与信任的朋友或家人倾诉

📌 如症状持续超过2周，请务必寻求专业帮助。心理咨询中心随时为你提供支持。
        """,
        "压力": """
【学业压力调节参考】

常见表现：
- 感到任务太多、时间不够
- 记忆力下降、效率降低
- 身体紧绷、 headaches、胃口改变

日常调节建议：
1. 任务分解：将大任务拆分为小步骤，逐一完成
2. 番茄工作法：学习25分钟 + 休息5分钟
3. 学会说"不"，合理拒绝过度负荷
4. 建立支持系统：与同学组队学习、互相鼓励

📌 适度压力是动力，过度压力需调节。如需帮助，欢迎预约咨询。
        """,
        "睡眠": """
【睡眠问题调节参考】

常见表现：
- 入睡困难，躺在床上超过30分钟无法入睡
- 易醒、早醒，睡眠质量差
- 白天精神不振

日常调节建议：
1. 睡前1小时远离电子屏幕
2. 建立固定的睡前仪式（如温水泡脚、听轻音乐）
3. 下午4点后避免摄入咖啡因
4. 卧室保持黑暗、安静、凉爽
5. 如果20分钟无法入睡，起床做些放松的事再回床

📌 如睡眠问题持续超过1个月，建议咨询专业人士。
        """,
        "人际": """
【人际关系困扰参考】

常见表现：
- 与室友/同学相处困难
- 社交回避，感到孤独
- 害怕被评价或拒绝
- 沟通中常产生误解

日常调节建议：
1. 学习非暴力沟通：观察 → 感受 → 需要 → 请求
2. 先倾听、再表达，避免急于辩解
3. 接纳差异，尊重边界
4. 从小范围社交开始，逐步建立信心

📌 人际困扰是大学生活中的常见挑战，心理咨询中心提供人际团体辅导，欢迎了解。
        """
    }
    
    return guides.get(issue_type, f"暂无【{issue_type}】的专项指导。建议预约心理咨询师进行一对一评估。")


@tool
def book_counseling(student_id: str, preferred_time: str, issue_brief: str) -> str:
    """
    预约心理咨询（模拟）
    
    Args:
        student_id: 学号
        preferred_time: 期望时间（如：下周三下午）
        issue_brief: 咨询主题简述
    """
    return f"【心理咨询预约申请已提交】\n学号：{student_id}\n期望时间：{preferred_time}\n咨询主题：{issue_brief}\n\n预约状态：待确认\n工作人员将在1个工作日内通过电话或短信与你联系，确认具体时间。\n\n📍 咨询地点：大学生活动中心三楼 301 室\n📞 如需改期请致电：010-87654321"


@tool
def emergency_help() -> str:
    """紧急情况求助信息"""
    return """
【心理紧急情况求助通道】

如果你或你身边的人正在经历心理危机（如自伤/自杀念头、严重 panic attack、精神恍惚等），请立即寻求帮助：

🚨 校内紧急联系：
- 心理咨询中心 24小时热线：010-8765-9999
- 学校保卫处：010-8765-0000
- 校医院急诊：010-8765-1111

🚨 校外专业资源：
- 全国24小时心理援助热线：400-161-9995
- 北京心理危机研究与干预中心：010-82951332
- 全国生命热线：400-821-1215

⚠️ 请记住：
- 求助是勇敢的表现，不是软弱
- 心理危机就像身体发烧一样，需要及时治疗
- 你并不孤单，总有人愿意帮助你
    """


class PsychologyAgent(BaseAgent):
    """心理咨询智能体"""
    
    def __init__(self):
        super().__init__(
            name="心理咨询智能体",
            description="提供心理支持、情绪疏导、心理健康知识和心理咨询预约服务"
        )
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.4,
            max_tokens=2048
        )
        self.tools = [
            self_assessment_guide,
            book_counseling,
            emergency_help
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.rag_service = RAGService()

    async def _build_knowledge_context(self, query: str) -> str:
        """检索知识库并格式化上下文"""
        results = await self.rag_service.search(query, top_k=3, agent_type="psychology")
        if not results:
            return ""
        context = "\n\n【知识库参考信息】\n"
        for r in results:
            snippet = r['content'][:400] + ('...' if len(r['content']) > 400 else '')
            context += f"· [{r['title']}] {snippet}\n"
        return context
    
    async def stream_process(self, message: str, session_id: str, context: Dict = None) -> AsyncGenerator[Dict, None]:
        """流式处理心理咨询相关请求"""
        
        system_prompt = """你是一位温暖、专业的心理陪伴助手。你的核心定位是提供非临床的心理支持和情绪陪伴。
【角色设定】
- 语气：温暖、共情、耐心、非评判
- 风格：像一位友善的心理咨询师，但明确声明你不是医生
- 边界：不诊断、不开处方、不制定治疗方案
【核心能力】
1. 情绪倾听与共情：反映用户的感受，让用户感到被理解
2. 心理科普：用通俗易懂的语言解释心理学概念
3. 自助技巧引导：教授CBT、正念、情绪调节等经实证支持的自助技巧
4. 危机识别：识别自杀、自伤、伤人风险信号
5. 资源转介：推荐专业帮助资源
【绝对禁止】
- 诊断任何心理疾病
- 建议开始、停止或调整药物
- 提供具体的治疗方案
- 对危机情况仅提供一般性安慰而不转介
- 收集用户真实身份信息
【危机协议】
如果用户表达自杀/自伤/伤人意念：
1. 立即表达关切并直接询问风险
2. 提供危机热线：400-161-9995（希望24热线）
3. 建议拨打110/120
4. 建议不要独处、移除致命工具
5. 持续陪伴直到用户联系到帮助
【开场白】
首次对话时，必须告知：
"我是你的心理陪伴助手，提供情绪支持和心理科普。我不能替代专业心理咨询师或医生的诊断和治疗。如果你面临严重心理困扰，我会建议你寻求专业帮助。"
【知识库引用】
回答问题时，优先基于提供的知识库内容。如果知识库中没有相关信息，坦诚告知，不编造。"""

        knowledge_context = await self._build_knowledge_context(message)
        full_prompt = system_prompt + knowledge_context

        messages = [SystemMessage(content=full_prompt)]
        
        conversation_history = []
        if context and hasattr(context, 'get'):
            conversation_history = context.get("history", [])
        for hist in conversation_history:
            if hist["role"] == "user":
                messages.append(HumanMessage(content=hist["content"]))
            else:
                messages.append(AIMessage(content=hist["content"]))
        
        messages.append(HumanMessage(content=message))
        
        try:
            response = await self.llm_with_tools.ainvoke(messages)
            
            if response.tool_calls:
                tool_messages = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    
                    for tool_func in self.tools:
                        if tool_func.name == tool_name:
                            result = await tool_func.ainvoke(tool_args) if hasattr(tool_func, 'ainvoke') else tool_func.invoke(tool_args)
                            if hasattr(result, 'content'):
                                result = result.content
                            tool_messages.append(ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call.get('id', '')
                            ))
                            break
                
                final_messages = messages + [response] + tool_messages
                full_content = ""
                async for chunk in self.llm.astream(final_messages):
                    content = chunk.content if hasattr(chunk, "content") else str(chunk)
                    if content:
                        full_content += content
                        for char in content:
                            yield {"type": "content", "content": char}
                action_taken = f"执行了 {len(tool_messages)} 个工具操作"
                yield {
                    "type": "done",
                    "content": AgentResponse(
                        content=full_content,
                        agent_type="psychology",
                        action_taken=action_taken
                    )
                }
            else:
                final_content = response.content
                for char in final_content:
                    yield {"type": "content", "content": char}
                yield {
                    "type": "done",
                    "content": AgentResponse(
                        content=final_content,
                        agent_type="psychology",
                        action_taken=None
                    )
                }
            
        except Exception as e:
            error_message = f"抱歉，处理您的请求时出现错误：{str(e)}。如果你正经历困扰，请直接拨打心理咨询中心热线：010-87654321。"
            yield {"type": "content", "content": error_message}
            yield {"type": "done", "content": AgentResponse(content=error_message, agent_type="psychology", action_taken="error")}
