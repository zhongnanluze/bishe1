"""
制度查询智能体
处理：学校规章制度、学籍管理、奖助学金政策、宿舍管理规定等查询
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
def query_policy(category: str, keyword: str = None) -> str:
    """
    查询学校规章制度（模拟数据库查询）
    
    Args:
        category: 制度类别（学籍管理/奖助学金/宿舍管理/考试纪律/学位授予/违纪处分/社会实践）
        keyword: 关键词（可选）
    """
    policies = {
        "学籍管理": """
【学籍管理制度要点】

1. 入学与注册
   - 新生须在录取通知书规定期限内报到
   - 每学期开学须按时注册，逾期两周视为自动退学

2. 转专业
   - 申请时间：大一第二学期末
   - 条件：成绩排名前30%，无违纪记录
   - 流程：申请 → 考核 → 公示 → 异动

3. 休学与复学
   - 休学一般1年，累计不超过2年
   - 复学前须提交复学申请和健康证明

4. 退学
   - 情形：学业不达标、逾期不注册、本人申请等
   - 退学学生须在2周内办理离校手续

5. 毕业与学位
   - 修满培养方案规定学分
   - 平均学分绩点≥2.0
   - 通过学位论文答辩
        """,
        "奖助学金": """
【奖助学金政策要点】

1. 国家奖学金
   - 金额：8000元/年
   - 条件：成绩优异，综合测评前10%
   - 申请时间：每年9月

2. 国家励志奖学金
   - 金额：5000元/年
   - 条件：家庭经济困难 + 成绩优秀

3. 国家助学金
   - 金额：2000-4000元/年（分档）
   - 条件：家庭经济困难认定
   - 申请时间：每年9-10月

4. 校级奖学金
   - 一等：3000元 | 二等：2000元 | 三等：1000元
   - 比例：不超过年级人数的30%

5. 勤工助学
   - 岗位：图书馆、实验室、行政部门等
   - 酬金：原则上不低于12元/小时
        """,
        "宿舍管理": """
【宿舍管理规定要点】

1. 作息时间
   - 宿舍楼门禁时间：23:00（周末顺延30分钟）
   - 熄灯时间：23:30（考试周延长至24:00）

2. 访客管理
   - 异性访客不得进入宿舍楼
   - 同性访客须在值班室登记，22:00前离开

3. 安全规定
   - 禁止使用大功率电器（>800W）
   - 禁止私拉电线、使用明火
   - 禁止饲养宠物

4. 卫生检查
   - 每周三下午统一检查
   - 评分纳入综合素质测评

5. 调换与退宿
   - 调换须双方同意 + 辅导员审批 + 宿管中心备案
   - 毕业/休学/转学须办理退宿手续
        """,
        "考试纪律": """
【考试纪律规定要点】

1. 考场规则
   - 提前15分钟进入考场，按指定位置就坐
   - 携带学生证/校园卡 + 必要文具
   - 手机等电子设备须关机并放在指定位置

2. 违纪行为
   - 携带与考试内容相关的资料
   - 抄袭他人答案或协助他人抄袭
   - 使用通讯设备
   - 替考或被替考

3. 处分等级
   - 警告：携带违规资料未使用
   - 严重警告：偷看、交头接耳
   - 记过：抄袭、使用通讯设备
   - 留校察看：组织作弊、替考
   - 开除学籍：二次作弊、集体作弊

4. 申诉
   - 对处分有异议可在5个工作日内提出书面申诉
        """,
        "学位授予": """
【学位授予规定要点】

1. 学士学位授予条件
   - 修满培养方案全部学分
   - 平均学分绩点≥2.0
   - 通过毕业论文（设计）答辩
   - 达到学校规定的外语水平要求
   - 无处分或处分已解除

2. 不授予学位的情形
   - 平均学分绩点<2.0
   - 毕业论文（设计）不合格
   - 考试作弊受记过及以上处分（未解除）
   - 在校学习时间超过最长学习年限

3. 学位论文要求
   - 查重率≤20%
   - 格式符合学校规范
   - 答辩委员会半数以上同意

4. 补授学位
   - 因绩点或外语未达标者，可在毕业后2年内申请补授
        """,
        "违纪处分": """
【学生违纪处分规定要点】

1. 处分种类
   - 警告
   - 严重警告
   - 记过
   - 留校察看（期限一般为12个月）
   - 开除学籍

2. 可减轻处分的情形
   - 主动承认错误并如实交代
   - 主动检举他人违纪行为
   - 违纪后积极挽回损失

3. 处分解除
   - 警告、严重警告：6个月后可申请解除
   - 记过：12个月后可申请解除
   - 留校察看：期满后自动解除，表现优异可提前

4. 申诉程序
   - 收到处分决定后5个工作日内提出书面申诉
   - 学生申诉处理委员会15个工作日内作出复查决定
        """,
        "社会实践": """
【社会实践制度要点】

1. 学分要求
   - 本科生须完成至少2个社会实践学分
   - 通常在第二至第六学期完成

2. 实践类型
   - 志愿服务（≥40小时/学分）
   - 社会调研（提交调研报告）
   - 专业实习（由学院统一安排）
   - 创新创业项目

3. 认定流程
   - 学生提交实践材料
   - 指导教师审核
   - 学院认定学分

4. 优秀实践
   - 每年评选校级优秀社会实践团队和个人
   - 优秀成果可推荐参加省级、国家级评选
        """
    }
    
    result = policies.get(category)
    if result:
        result = result + "\n\n⚠️ 以上制度摘要仅供参考，具体条款以学校最新官方文件为准。如有疑问，建议咨询相关部门。"
    else:
        result = f"抱歉，暂未找到【{category}】的制度信息。建议：\n1. 查询学校官网最新文件\n2. 咨询相关部门\n3. 在知识库管理中上传相关制度文件"
    if keyword:
        result += f"\n\n（查询关键词：{keyword}）"
    return result


@tool
def query_department_contact(department: str) -> str:
    """
    查询相关部门联系方式
    
    Args:
        department: 部门名称（教务处/学生处/宿管中心/财务处/图书馆/保卫处/心理咨询中心）
    """
    contacts = {
        "教务处": "📍 行政楼201 | 📞 010-11112222 | 📧 jwc@university.edu.cn | ⏰ 8:30-11:30, 14:00-17:00",
        "学生处": "📍 行政楼301 | 📞 010-22223333 | 📧 xsc@university.edu.cn | ⏰ 8:30-11:30, 14:00-17:00",
        "宿管中心": "📍 后勤楼102 | 📞 010-33334444 | 📧 sgzx@university.edu.cn | ⏰ 8:00-22:00",
        "财务处": "📍 行政楼105 | 📞 010-44445555 | 📧 cwc@university.edu.cn | ⏰ 8:30-11:30, 14:00-16:30（周二、四收费）",
        "图书馆": "📍 图书馆总馆 | 📞 010-55556666 | 📧 lib@university.edu.cn | ⏰ 8:00-22:00",
        "保卫处": "📍 校门口东侧 | 📞 010-66667777（24小时）| 📧 bwc@university.edu.cn",
        "心理咨询中心": "📍 大学生活动中心301 | 📞 010-87654321 | 📧 counseling@university.edu.cn | ⏰ 9:00-17:00"
    }
    
    return contacts.get(department, f"暂无【{department}】的联系方式。建议拨打学校总机查询：010-88889999")


class PolicyAgent(BaseAgent):
    """制度查询智能体"""
    
    def __init__(self):
        super().__init__(
            name="制度查询智能体",
            description="查询学校各类规章制度、政策文件、管理办法和相关办事部门信息"
        )
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.2,
            max_tokens=2048
        )
        self.tools = [
            query_policy,
            query_department_contact
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.rag_service = RAGService()

    async def _build_knowledge_context(self, query: str) -> str:
        """检索知识库并格式化上下文"""
        results = await self.rag_service.search(query, top_k=3, agent_type="policy")
        if not results:
            return ""
        context = "\n\n【知识库参考信息】\n"
        for r in results:
            snippet = r['content'][:400] + ('...' if len(r['content']) > 400 else '')
            context += f"· [{r['title']}] {snippet}\n"
        return context
    
    async def process(self, message: str, session_id: str, context: Dict = None) -> AgentResponse:
        """处理制度查询相关请求"""
        
        system_prompt = """你是文泽奇妙小AI的制度查询助手，一位严谨、清晰且耐心的校园政策专家。你的职责是帮助学生快速准确地了解学校各项规章制度。

你的职责：
- 学籍制度：入学、注册、转专业、休学、退学、毕业、学位授予等
- 奖助学金：国家奖学金、助学金、校级奖学金、勤工助学等政策
- 宿舍管理：作息、访客、安全、卫生、调换等规定
- 考试纪律：考场规则、违纪认定、处分等级、申诉程序
- 违纪处分：处分种类、期限、解除条件、申诉渠道
- 部门查询：提供相关办事部门的地址、电话、办公时间

服务风格：
- 表述准确、条理清晰，使用编号和分点
- 引用制度时注明"根据学校XX规定"
- 对于不确定的内容，坦诚说明并建议咨询相关部门
- 语气正式但不失亲切

重要准则：
- 优先使用知识库中的最新制度信息
- 制度可能存在更新，建议学生以学校官网或官方文件为准
- 涉及个人具体情况的制度适用问题，建议咨询相关部门
- **严禁编造任何制度条款**：如果知识库和工具中都没有相关信息，必须明确告知用户"该制度信息我暂时无法确认，建议咨询相关部门或查阅学校官网最新文件"
- 不要猜测、不要推断、不要补充未经验证的细节
- 工具函数返回的参考信息仅为示例，必须明确提示用户"以下信息仅供参考，请以学校最新官方文件为准"

请使用提供的工具函数来查询制度信息，确保回答有据可依。"""

        knowledge_context = await self._build_knowledge_context(message)
        if not knowledge_context:
            knowledge_context = "\n\n【知识库检索结果】未找到与该问题相关的制度内容。请注意：如果没有可靠信息来源，请不要编造任何制度条款或政策细节。\n"
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
                agent_type="policy",
                action_taken=action_taken
            )

        except Exception as e:
            return AgentResponse(
                content=f"抱歉，查询制度信息时出现错误：{str(e)}。建议直接访问学校官网或拨打相关部门电话咨询。",
                agent_type="policy",
                action_taken="error"
            )

    async def stream_process(self, message: str, session_id: str, context: Dict = None) -> AsyncGenerator[Dict, None]:
        """流式处理制度查询相关请求"""
        
        system_prompt = """你是文泽奇妙小AI的制度查询助手，一位严谨、清晰且耐心的校园政策专家。你的职责是帮助学生快速准确地了解学校各项规章制度。

你的职责：
- 学籍制度：入学、注册、转专业、休学、退学、毕业、学位授予等
- 奖助学金：国家奖学金、助学金、校级奖学金、勤工助学等政策
- 宿舍管理：作息、访客、安全、卫生、调换等规定
- 考试纪律：考场规则、违纪认定、处分等级、申诉程序
- 违纪处分：处分种类、期限、解除条件、申诉渠道
- 部门查询：提供相关办事部门的地址、电话、办公时间

服务风格：
- 表述准确、条理清晰，使用编号和分点
- 引用制度时注明"根据学校XX规定"
- 对于不确定的内容，坦诚说明并建议咨询相关部门
- 语气正式但不失亲切

重要准则：
- 优先使用知识库中的最新制度信息
- 制度可能存在更新，建议学生以学校官网或官方文件为准
- 涉及个人具体情况的制度适用问题，建议咨询相关部门
- 不要编造不存在的制度条款
- 当知识库中没有相关信息时，可调用模拟政策工具作为参考，但需提示用户核实

请使用提供的工具函数来查询制度信息，确保回答有据可依。"""

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
                    agent_type="policy",
                    action_taken=action_taken
                )
            }
            
        except Exception as e:
            error_message = f"抱歉，查询制度信息时出现错误：{str(e)}。建议直接访问学校官网或拨打相关部门电话咨询。"
            yield {"type": "content", "content": error_message}
            yield {"type": "done", "content": AgentResponse(content=error_message, agent_type="policy", action_taken="error")}
