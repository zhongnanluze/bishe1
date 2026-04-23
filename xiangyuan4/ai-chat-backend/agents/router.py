"""
智能体路由系统
负责根据用户意图选择最合适的智能体
"""

from typing import Dict, Optional, List
from enum import Enum
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env_utils import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


class AgentType(Enum):
    """智能体类型枚举"""
    ACADEMIC = "academic"                # 学生学业
    STUDENT_SERVICES = "student_services" # 学生办事
    PSYCHOLOGY = "psychology"            # 心理咨询
    POLICY = "policy"                    # 制度查询
    CHAT = "chat"                        # 日常聊天


class AgentRouter:
    """
    智能体路由器
    使用LLM分析用户意图，选择最合适的智能体
    """
    
    def __init__(self):
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.1,
            max_tokens=512
        )
        
        # 智能体描述信息
        self.agent_descriptions = {
            AgentType.ACADEMIC: {
                "name": "学生学业智能体",
                "description": "处理学生学业相关需求",
                "capabilities": [
                    "选课、退课",
                    "课表查询",
                    "成绩查询",
                    "GPA计算",
                    "学业日历查询",
                    "课程搜索"
                ],
                "keywords": ["选课", "退课", "课表", "课程", "成绩", "GPA", "学分", "考试", "学期", "学业", "教务", "教室", "排课", "挂科", "补考", "重修", "学分绩", "绩点", "培养方案", "毕业要求"]
            },
            AgentType.STUDENT_SERVICES: {
                "name": "学生办事智能体",
                "description": "处理学生办事相关需求",
                "capabilities": [
                    "证件补办（校园卡、学生证）",
                    "学费缴纳",
                    "饭卡充值",
                    "办事流程查询（请假、休学、转专业、奖学金申请等）",
                    "学生事务中心信息查询"
                ],
                "keywords": ["证件", "补办", "学费", "缴纳", "饭卡", "充值", "请假", "休学", "转专业", "奖学金", "宿舍", "流程", "事务中心", "办事", "校园卡", "学生证", "证明", "缴费", "报销", "医保", "银行卡", "落户", "档案"]
            },
            AgentType.PSYCHOLOGY: {
                "name": "心理咨询智能体",
                "description": "提供心理支持和心理健康服务",
                "capabilities": [
                    "情绪疏导与倾听",
                    "心理压力调节建议",
                    "心理咨询预约信息",
                    "心理健康知识科普",
                    "紧急心理危机求助"
                ],
                "keywords": ["心理", "压力", "焦虑", "抑郁", "情绪", "失眠", "孤独", "自卑", "人际", "恋爱", "咨询", "预约", "辅导", "疏导", "心理咨询", "心理健康", "心情不好", "难受", "想哭", "迷茫", "自卑", "紧张", "害怕", "恐惧", " suicide", "自残", "活着没意思", "不想活"]
            },
            AgentType.POLICY: {
                "name": "制度查询智能体",
                "description": "查询学校各类规章制度和政策",
                "capabilities": [
                    "学籍管理制度",
                    "奖助学金政策",
                    "宿舍管理规定",
                    "考试纪律",
                    "学位授予条件",
                    "违纪处分规定",
                    "部门联系方式"
                ],
                "keywords": ["制度", "规定", "规章", "政策", "学籍", "学位", "毕业", "违纪", "处分", "守则", "管理办法", "细则", "条例", "校规", "宿舍管理", "晚归", "请假制度", "奖学金政策", "助学金", "学分要求", "培养方案", "学位授予", "考试纪律", "作弊", "申诉", "规章制度"]
            },
            AgentType.CHAT: {
                "name": "日常聊天智能体",
                "description": "处理校园生活闲聊和一般性咨询",
                "capabilities": [
                    "校园生活闲聊",
                    "一般性问题解答",
                    "问候和寒暄",
                    "校园设施位置咨询",
                    "生活小贴士"
                ],
                "keywords": ["你好", "谢谢", "再见", "嗨", "哈喽", "在吗", "帮忙", "早上好", "晚上好", "闲聊", "笑话", "天气", "吃饭", "食堂", "推荐", "好玩", "附近", "周边", "快递", "超市", "银行", "医院", "谢谢", "拜拜", "嗯", "哦", "好的", "知道了"]
            }
        }
    
    async def route(self, message: str, conversation_history: List[Dict] = None) -> AgentType:
        """
        根据用户消息路由到合适的智能体
        
        Args:
            message: 用户输入消息
            conversation_history: 对话历史
            
        Returns:
            AgentType: 选择的智能体类型
        """
        # 使用关键词匹配进行快速路由
        return self._fallback_route(message)
    
    def _build_router_prompt(self) -> str:
        """构建路由决策提示词"""
        
        prompt = """你是一个智能路由系统，负责分析用户意图并将请求分配给最合适的智能体。

可选择的智能体：

1. **学生学业智能体** (academic)
   - 处理选课、退课
   - 查询课表、成绩、GPA
   - 学业日历、课程搜索
   - 培养方案、毕业要求

2. **学生办事智能体** (student_services)
   - 证件补办（校园卡、学生证）
   - 学费缴纳、饭卡充值
   - 办事流程查询（请假、休学、转专业等）
   - 各类证明开具

3. **心理咨询智能体** (psychology)
   - 情绪疏导与倾听
   - 心理压力调节建议
   - 心理咨询预约信息
   - 紧急心理危机求助

4. **制度查询智能体** (policy)
   - 学籍管理制度
   - 奖助学金政策
   - 宿舍管理规定
   - 考试纪律、违纪处分

5. **日常聊天智能体** (chat)
   - 校园生活闲聊
   - 一般性咨询
   - 问候和寒暄
   - 生活小贴士

请分析用户消息，选择最合适的智能体。

返回格式（JSON）：
{
    "agent_type": "academic | student_services | psychology | policy | chat",
    "confidence": 0.0-1.0,
    "reasoning": "选择理由"
}

注意：
- 如果用户消息涉及多个领域，选择最主要的一个
- 如果无法确定，选择 "chat"
- confidence 表示你对这个决策的信心程度"""
        
        return prompt
    
    def _parse_router_response(self, response: str) -> Dict:
        """解析路由决策响应"""
        try:
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    return json.loads(json_str)
            except:
                pass
            
            return {"agent_type": "chat", "confidence": 0.5}
    
    def _fallback_route(self, message: str) -> AgentType:
        """
        后备路由方案：基于关键词匹配
        
        Args:
            message: 用户消息
            
        Returns:
            AgentType: 匹配的智能体类型
        """
        message_lower = message.lower()
        
        # 计算每个智能体的匹配分数
        scores = {}
        for agent_type, info in self.agent_descriptions.items():
            score = 0
            for keyword in info["keywords"]:
                if keyword in message_lower:
                    score += 1
            scores[agent_type] = score
        
        # 选择分数最高的智能体
        best_match = max(scores, key=scores.get)
        
        # 如果都没有匹配，返回日常聊天
        if scores[best_match] == 0:
            return AgentType.CHAT
        
        return best_match
    
    def get_agent_info(self, agent_type: AgentType) -> Dict:
        """获取智能体信息"""
        return self.agent_descriptions.get(agent_type, {})
