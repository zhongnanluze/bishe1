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
    STUDENT_AFFAIRS = "student_affairs"  # 学生事务
    ACADEMIC = "academic"                # 学业相关
    GENERAL = "general"                  # 通用对话


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
            temperature=0.1,  # 低温度，确保路由决策稳定
            max_tokens=512
        )
        
        # 智能体描述信息
        self.agent_descriptions = {
            AgentType.STUDENT_AFFAIRS: {
                "name": "学生事务智能体",
                "description": "处理学生事务相关需求",
                "capabilities": [
                    "证件补办（校园卡、学生证）",
                    "学费缴纳",
                    "饭卡充值",
                    "办事流程查询（请假、休学、转专业、奖学金申请等）",
                    "学生事务中心信息查询"
                ],
                "keywords": ["证件", "补办", "学费", "缴纳", "饭卡", "充值", "请假", "休学", "转专业", "奖学金", "宿舍", "流程", "事务中心"]
            },
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
                "keywords": ["选课", "退课", "课表", "课程", "成绩", "GPA", "学分", "考试", "学期", "学业", "教务", "教室"]
            },
            AgentType.GENERAL: {
                "name": "通用助手",
                "description": "处理一般性对话和咨询",
                "capabilities": [
                    "校园生活咨询",
                    "一般性问题解答",
                    "问候和闲聊"
                ],
                "keywords": ["你好", "谢谢", "再见", "帮助", "请问"]
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
        # 使用关键词匹配进行快速路由，避免 LLM 调用阻塞流式输出
        return self._fallback_route(message)
    
    def _build_router_prompt(self) -> str:
        """构建路由决策提示词"""
        
        prompt = """你是一个智能路由系统，负责分析用户意图并将请求分配给最合适的智能体。

可选择的智能体：

1. **学生事务智能体** (student_affairs)
   - 处理证件补办（校园卡、学生证）
   - 处理学费缴纳
   - 处理饭卡充值
   - 查询办事流程（请假、休学、转专业、奖学金申请等）
   - 学生事务中心相关咨询

2. **学生学业智能体** (academic)
   - 处理选课、退课
   - 查询课表
   - 查询成绩、GPA
   - 学业日历查询
   - 课程搜索

3. **通用助手** (general)
   - 处理一般性咨询
   - 校园生活问题
   - 问候和闲聊

请分析用户消息，选择最合适的智能体。

返回格式（JSON）：
{
    "agent_type": "student_affairs | academic | general",
    "confidence": 0.0-1.0,
    "reasoning": "选择理由"
}

注意：
- 如果用户消息涉及多个领域，选择最主要的一个
- 如果无法确定，选择 "general"
- confidence 表示你对这个决策的信心程度"""
        
        return prompt
    
    def _parse_router_response(self, response: str) -> Dict:
        """解析路由决策响应"""
        try:
            # 尝试直接解析JSON
            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试从文本中提取JSON
            try:
                # 查找JSON块
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = response[start:end]
                    return json.loads(json_str)
            except:
                pass
            
            # 如果都失败，使用关键词匹配
            return {"agent_type": "general", "confidence": 0.5}
    
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
        
        # 如果都没有匹配，返回通用助手
        if scores[best_match] == 0:
            return AgentType.GENERAL
        
        return best_match
    
    def get_agent_info(self, agent_type: AgentType) -> Dict:
        """获取智能体信息"""
        return self.agent_descriptions.get(agent_type, {})
