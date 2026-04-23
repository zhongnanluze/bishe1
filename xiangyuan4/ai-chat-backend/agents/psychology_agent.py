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
def query_counseling_center() -> str:
    """查询学校心理咨询中心信息"""
    return """
【学校心理咨询中心】

📍 地址：大学生活动中心三楼 301 室
⏰ 开放时间：周一至周五 9:00-17:00（节假日除外）
📞 预约电话：010-87654321
📧 邮箱：counseling@university.edu.cn
🌐 在线预约：http://xljk.university.edu.cn

💡 服务内容：
- 个体心理咨询（每次50分钟，免费）
- 团体心理辅导
- 心理测评与档案
- 心理危机干预
- 心理健康讲座

👨‍⚕️ 咨询师团队：
- 专职心理咨询师 6 名
- 兼职心理咨询师 10 名
- 所有咨询师均具备国家二级心理咨询师资质

⚠️ 预约须知：
- 请提前1-2天预约
- 如临时无法到场，请提前取消
- 咨询内容严格保密（涉及安全风险除外）
    """


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
            query_counseling_center,
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
    
    async def process(self, message: str, session_id: str, context: Dict = None) -> AgentResponse:
        """处理心理咨询相关请求"""
        
        system_prompt = """你是文泽奇妙小AI的心理咨询助手，一位温暖、专业且富有同理心的心理支持者。你的存在是为了让每一位学生感受到被理解、被接纳。

你的职责：
- 情绪倾听与疏导：认真倾听用户的困扰，给予情感上的支持和理解
- 心理健康科普：介绍常见心理问题的识别与调节方法
- 心理咨询预约：协助学生了解并预约学校心理咨询服务
- 危机识别与转介：识别可能的危机信号，及时引导至专业帮助

服务风格：
- 语气温和、充满同理心，避免评判和说教
- 使用"我感受到...""听起来你..."等共情表达
- 给予希望感，让用户知道困扰是暂时的、可应对的
- 不诊断、不开药方，始终引导至专业资源
- 适当使用表情符号，传递温暖

重要准则：
- 你不是医生，不能做出医学诊断
- 当用户表达自伤/自杀念头时，立即提供紧急求助信息
- 鼓励用户在需要时寻求学校心理咨询中心的专业帮助
- 保护用户隐私，不追问过多个人信息
- 当用户询问心理健康知识时，优先参考知识库信息作答
- **严禁编造任何信息**：如果知识库或工具中没有相关信息，必须明确告知用户"这个问题我暂时无法确认，建议咨询学校心理咨询中心的专业老师"
- 不要猜测、不要推断、不要使用未经验证的信息
- 心理自评指导仅供参考，不能替代专业诊断

请记住：你的每一句话都可能给用户带来温暖和力量。"""

        knowledge_context = await self._build_knowledge_context(message)
        if not knowledge_context:
            knowledge_context = "\n\n【知识库检索结果】未找到与该问题相关的知识库内容。请注意：如果没有可靠信息来源，请不要编造答案。\n"
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
                final_response = await self.llm.ainvoke(final_messages)
                final_content = final_response.content
                action_taken = f"执行了 {len(tool_messages)} 个工具操作"
            else:
                final_content = response.content
                action_taken = None
            
            return AgentResponse(
                content=final_content,
                agent_type="psychology",
                action_taken=action_taken
            )

        except Exception as e:
            return AgentResponse(
                content=f"抱歉，处理您的请求时出现错误：{str(e)}。如果你正经历困扰，请直接拨打心理咨询中心热线：010-87654321。",
                agent_type="psychology",
                action_taken="error"
            )

    async def stream_process(self, message: str, session_id: str, context: Dict = None) -> AsyncGenerator[Dict, None]:
        """流式处理心理咨询相关请求"""
        
        system_prompt = """你是文泽奇妙小AI的心理咨询助手，一位温暖、专业且富有同理心的心理支持者。你的存在是为了让每一位学生感受到被理解、被接纳。

你的职责：
- 情绪倾听与疏导：认真倾听用户的困扰，给予情感上的支持和理解
- 心理健康科普：介绍常见心理问题的识别与调节方法
- 心理咨询预约：协助学生了解并预约学校心理咨询服务
- 危机识别与转介：识别可能的危机信号，及时引导至专业帮助

服务风格：
- 语气温和、充满同理心，避免评判和说教
- 使用"我感受到...""听起来你..."等共情表达
- 给予希望感，让用户知道困扰是暂时的、可应对的
- 不诊断、不开药方，始终引导至专业资源
- 适当使用表情符号，传递温暖

重要准则：
- 你不是医生，不能做出医学诊断
- 当用户表达自伤/自杀念头时，立即提供紧急求助信息
- 鼓励用户在需要时寻求学校心理咨询中心的专业帮助
- 保护用户隐私，不追问过多个人信息
- 当用户询问心理健康知识时，优先参考知识库信息作答
- 不要编造你不确定的信息

请记住：你的每一句话都可能给用户带来温暖和力量。"""

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
                final_response = await self.llm.ainvoke(final_messages)
                final_content = final_response.content
                action_taken = f"执行了 {len(tool_messages)} 个工具操作"
            else:
                final_content = response.content
                action_taken = None
            
            for char in final_content:
                yield {"type": "content", "content": char}
            
            yield {
                "type": "done",
                "content": AgentResponse(
                    content=final_content,
                    agent_type="psychology",
                    action_taken=action_taken
                )
            }
            
        except Exception as e:
            error_message = f"抱歉，处理您的请求时出现错误：{str(e)}。如果你正经历困扰，请直接拨打心理咨询中心热线：010-87654321。"
            yield {"type": "content", "content": error_message}
            yield {"type": "done", "content": AgentResponse(content=error_message, agent_type="psychology", action_taken="error")}
