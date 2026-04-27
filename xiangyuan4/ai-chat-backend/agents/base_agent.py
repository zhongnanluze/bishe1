"""
智能体基类
定义所有智能体的通用接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass

from langchain.agents import create_agent


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
    async def stream_process(self, message: str, session_id: str, context: Dict = None) -> AsyncGenerator[Dict, None]:
        """
        流式处理用户消息，边生成边输出

        Args:
            message: 用户输入消息
            session_id: 会话ID
            context: 上下文信息

        Yields:
            Dict: 包含 'type' 和 'content' 的字典
                  type='content' 时，content 是生成的文本片段
                  type='done' 时，content 是完整的 AgentResponse
                  type='error' 时，content 是错误信息
        """
        pass

    def add_to_history(self, role: str, content: str):
        """添加对话历史"""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]

    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.conversation_history.copy()

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history.clear()