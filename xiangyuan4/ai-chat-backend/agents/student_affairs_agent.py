"""
学生事务智能体
处理：证件补办、学费缴纳、饭卡充值、办事流程查询
"""

from typing import Dict, Optional
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from .base_agent import BaseAgent, AgentResponse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env_utils import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


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
    # 模拟办理流程
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
    # 模拟缴费流程
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
    # 模拟充值流程
    return f"【饭卡充值成功】\n学号：{student_id}\n充值金额：¥{amount}\n支付方式：{payment_method}\n\n当前余额：¥{amount + 50:.2f}\n充值时间：2024年\n可在食堂刷卡机或手机APP查询余额。"


@tool
def query_process(affair_type: str) -> str:
    """
    查询办事流程
    
    Args:
        affair_type: 事务类型（如：请假/休学/转专业/奖学金申请等）
    """
    # 流程知识库
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
    
    return processes.get(affair_type, f"抱歉，暂时没有找到【{affair_type}】的办理流程。请咨询学生事务中心：电话 010-12345678")


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


class StudentAffairsAgent(BaseAgent):
    """学生事务智能体"""
    
    def __init__(self):
        super().__init__(
            name="学生事务智能体",
            description="处理学生事务相关需求，包括证件补办、学费缴纳、饭卡充值、办事流程查询等"
        )
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=2048
        )
        # 绑定工具
        self.tools = [
            replace_id_card,
            pay_tuition,
            recharge_meal_card,
            query_process,
            query_affairs_center_info
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    async def process(self, message: str, session_id: str, context: Dict = None) -> AgentResponse:
        """处理学生事务相关请求"""
        
        # 系统提示词
        system_prompt = """你是学生事务智能助手，专门帮助学生处理各类校园事务。

你的职责：
1. 证件补办：校园卡、学生证等证件的补办申请
2. 学费缴纳：协助完成学费缴纳操作
3. 饭卡充值：帮助充值校园饭卡
4. 办事流程查询：提供各类事务的办理流程

注意事项：
- 办理业务前需要确认学生身份（学号）
- 耐心引导学生提供必要信息
- 对于复杂问题，分步骤指导办理
- 如果无法直接办理，提供详细的线下办理指引

请使用提供的工具函数来帮助学生完成事务办理。"""
        
        # 构建消息列表
        messages = [SystemMessage(content=system_prompt)]
        
        # 添加历史对话
        for hist in self.conversation_history:
            if hist["role"] == "user":
                messages.append(HumanMessage(content=hist["content"]))
            else:
                messages.append(AIMessage(content=hist["content"]))
        
        # 添加当前消息
        messages.append(HumanMessage(content=message))
        
        try:
            # 调用LLM
            response = self.llm_with_tools.invoke(messages)
            
            # 处理工具调用
            if response.tool_calls:
                # 执行工具调用
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    
                    # 找到对应的工具并执行
                    for tool_func in self.tools:
                        if tool_func.name == tool_name:
                            result = tool_func.invoke(tool_call)
                            tool_results.append(f"【{tool_name}】\n{result}")
                            break
                
                # 构建最终响应
                final_content = "\n\n".join(tool_results)
                action_taken = f"执行了 {len(tool_results)} 个工具操作"
            else:
                final_content = response.content
                action_taken = None
            
            # 更新历史
            self.add_to_history("user", message)
            self.add_to_history("assistant", final_content)
            
            return AgentResponse(
                content=final_content,
                agent_type="student_affairs",
                action_taken=action_taken
            )
            
        except Exception as e:
            return AgentResponse(
                content=f"抱歉，处理您的请求时出现错误：{str(e)}。请稍后重试或联系学生事务中心。",
                agent_type="student_affairs",
                action_taken="error"
            )
