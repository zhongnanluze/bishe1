"""
智能体基类
定义所有智能体的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class AgentResponse:
    """智能体响应数据结构"""
    content: str
    agent_type: str
    action_taken: Optional[str] = None
    data: Optional[Dict] = None


class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.conversation_history: List[Dict[str, str]] = []
    
    @abstractmethod
    async def process(self, message: str, session_id: str, context: Dict = None) -> AgentResponse:
        """
        处理用户消息
        
        Args:
            message: 用户输入消息
            session_id: 会话ID
            context: 上下文信息
            
        Returns:
            AgentResponse: 智能体响应
        """
        pass
    
    def add_to_history(self, role: str, content: str):
        """添加对话历史"""
        self.conversation_history.append({"role": role, "content": content})
        # 限制历史记录长度，保留最近20轮
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
    
    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.conversation_history.copy()
    
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
