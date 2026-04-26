"""
学生办事智能体
处理：证件补办、学费缴纳、饭卡充值、办事流程查询
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
def replace_id_card(student_id: str, id_card_type: str, reason: str) -> str:
    """
    补办证件
    
    Args:
        student_id: 学号
        id_card_type: 证件类型（校园卡/学生证/身份证）
        reason: 补办原因
    """
    return f"【证件补办申请已提交】\n学号：{student_id}\n证件类型：{id_card_type}\n原因：{reason}\n\n办理进度：审核中\n预计完成时间：3-5个工作日\n请携带身份证到学生事务中心领取新证。"


@tool
def pay_tuition(student_id: str, semester: str, amount: float, payment_method: str) -> str:
    """
    缴纳学费
    
    Args:
        student_id: 学号
        semester: 学期（如：2024-2025-1）
        amount: 金额（元）
        payment_method: 支付方式（微信支付/支付宝/银行卡）
    """
    return f"【学费缴纳成功】\n学号：{student_id}\n学期：{semester}\n金额：¥{amount}\n支付方式：{payment_method}\n\n交易单号：TXN{hash(student_id + semester) % 100000000:08d}\n缴费时间：2024年\n请保存好缴费凭证。"


@tool
def recharge_meal_card(student_id: str, amount: float, payment_method: str) -> str:
    """
    饭卡充值
    
    Args:
        student_id: 学号
        amount: 充值金额（元）
        payment_method: 支付方式（微信支付/支付宝/银行卡）
    """
    return f"【饭卡充值成功】\n学号：{student_id}\n充值金额：¥{amount}\n支付方式：{payment_method}\n\n当前余额：¥{amount + 50:.2f}\n充值时间：2024年\n可在食堂刷卡机或手机APP查询余额。"


@tool
def query_process(affair_type: str) -> str:
    """
    查询办事流程
    
    Args:
        affair_type: 事务类型（如：请假/休学/转专业/奖学金申请等）
    """
    processes = {
        "请假": """
【请假流程】
1. 登录教务系统填写请假申请
2. 辅导员审批
3. 学院审批（3天以上）
4. 销假（返校后）

所需材料：
- 病假：医院证明
- 事假：家长知情同意书
        """,
        "休学": """
【休学流程】
1. 提交休学申请书
2. 家长签字同意
3. 学院审核
4. 教务处审批
5. 办理离校手续

注意事项：
- 休学时间一般为1年
- 累计不超过2年
        """,
        "转专业": """
【转专业流程】
1. 关注转专业通知（每学期末）
2. 提交转专业申请
3. 参加转入学院考核
4. 公示录取名单
5. 办理学籍异动

申请条件：
- 大一或大二年级
- 成绩排名前30%
- 无违纪记录
        """,
        "奖学金申请": """
【奖学金申请流程】
1. 登录学工系统提交申请
2. 班级评议
3. 学院评审
4. 学校公示
5. 发放奖金

申请时间：每年9月
所需材料：成绩单、获奖证书、社会实践证明
        """,
        "宿舍调换": """
【宿舍调换流程】
1. 提交调换申请（说明原因）
2. 辅导员审核
3. 宿管中心审批
4. 办理调换手续

调换条件：
- 因身体原因
- 因学习需要
- 其他特殊情况
        """
    }
    
    result = processes.get(affair_type)
    if result:
        return result + "\n\n⚠️ 以上流程仅供参考，具体要求、材料和时限请以学校最新规定或学生事务中心告知为准。"
    return f"抱歉，暂时没有找到【{affair_type}】的办理流程。建议直接咨询学生事务中心：电话 010-12345678，或前往学生活动中心一楼现场咨询。"


@tool
def query_affairs_center_info() -> str:
    """查询学生事务中心信息"""
    return """
【学生事务中心信息】

📍 地址：学生活动中心一楼
⏰ 工作时间：周一至周五 8:30-17:00
📞 电话：010-12345678
📧 邮箱：affairs@university.edu.cn

💼 办理业务：
- 证件补办（校园卡、学生证）
- 学费缴纳咨询
- 饭卡充值
- 各类证明开具
- 办事流程咨询

🌐 在线服务：
- 教务系统：http://jw.university.edu.cn
- 学工系统：http://xg.university.edu.cn
    """


class StudentServicesAgent(BaseAgent):
    """学生办事智能体"""
    
    def __init__(self):
        super().__init__(
            name="学生办事智能体",
            description="处理学生办事相关需求，包括证件补办、学费缴纳、饭卡充值、办事流程查询等"
        )
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=2048
        )
        self.tools = [
            replace_id_card,
            pay_tuition,
            recharge_meal_card,
            query_process,
            query_affairs_center_info
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.rag_service = RAGService()

    async def _build_knowledge_context(self, query: str) -> str:
        """检索知识库并格式化上下文"""
        results = await self.rag_service.search(query, top_k=3, agent_type="student_services")
        if not results:
            return ""
        context = "\n\n【知识库参考信息】\n"
        for r in results:
            snippet = r['content'][:400] + ('...' if len(r['content']) > 400 else '')
            context += f"· [{r['title']}] {snippet}\n"
        return context
    
    async def stream_process(self, message: str, session_id: str, context: Dict = None) -> AsyncGenerator[Dict, None]:
        """流式处理学生办事相关请求，边生成边输出"""
        
        system_prompt = """你是文泽奇妙小AI的学生办事助手，一个友善、热情且专业的校园服务专家。你喜欢用轻松愉快的语气与学生交流，让校园生活变得更加便捷。

你的职责：
- 证件补办：校园卡、学生证等证件的补办申请，全程耐心指导
- 学费缴纳：协助完成学费缴纳操作，提供多种支付方式选择
- 饭卡充值：帮助充值校园饭卡，确保学生用餐无忧
- 办事流程查询：提供各类事务的详细办理流程，让学生少跑腿
- 校园生活咨询：回答图书馆、食堂、宿舍、校医院等相关问题

服务风格：
- 语气亲切友好，像朋友一样交流
- 主动关心学生需求，提供个性化建议
- 遇到复杂问题时，分步骤清晰指导
- 对于无法在线办理的事项，提供详细的线下办理指引
- 适当使用表情和语气词，让对话更有温度

工作准则：
- 办理业务前确认学生身份（学号）
- 保护学生个人信息安全
- 及时更新办理进度和相关信息
- 遇到问题时积极协助解决
- 当用户询问校园生活信息时，请优先参考知识库信息作答
- 不要编造你不确定的信息，优先使用知识库提供的内容

请使用提供的工具函数来帮助学生完成事务办理，让学生感受到校园服务的温暖和便捷！"""

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
                        agent_type="student_services",
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
                        agent_type="student_services",
                        action_taken=None
                    )
                }
            
        except Exception as e:
            error_message = f"抱歉，处理您的请求时出现错误：{str(e)}。请稍后重试或联系学生事务中心。"
            yield {"type": "content", "content": error_message}
            yield {"type": "done", "content": AgentResponse(content=error_message, agent_type="student_services", action_taken="error")}
