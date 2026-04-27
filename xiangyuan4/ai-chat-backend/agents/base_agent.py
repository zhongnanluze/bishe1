"""
智能体基类
定义所有智能体的通用接口，基于 LangChain create_agent 封装
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage


@dataclass
class AgentResponse:
    """智能体响应数据结构"""
    content: str
    agent_type: str
    action_taken: Optional[str] = None
    data: Optional[Dict] = None


class BaseAgent(ABC):
    """智能体基类"""

    def __init__(
        self,
        name: str,
        description: str,
        llm,
        tools: list,
        system_prompt: str,
        agent_type: str
    ):
        self.name = name
        self.description = description
        self.agent_type = agent_type
        self.conversation_history: List[Dict[str, str]] = []
        self.llm = llm
        self.tools = tools or []
        self.base_system_prompt = system_prompt

        # 使用 LangChain create_agent 创建智能体
        # system_prompt 设为 None，由 _run_stream 中手动构建完整 system message
        self.agent = create_agent(
            model=llm,
            tools=self.tools,
            system_prompt=None
        )

    async def _run_stream(
        self,
        message: str,
        session_id: str,
        context: Dict = None,
        knowledge_context: str = "",
        system_prompt: str = None
    ) -> AsyncGenerator[Dict, None]:
        """
        使用 create_agent 统一执行智能体并流式输出

        Args:
            message: 用户输入消息
            session_id: 会话ID
            context: 上下文信息（包含 history、user_info 等）
            knowledge_context: 知识库检索到的上下文文本
            system_prompt: 可选，临时覆盖的系统提示词
        """
        # 拼接完整系统提示词（角色设定 + 知识库上下文）
        full_system_prompt = system_prompt if system_prompt is not None else self.base_system_prompt
        if knowledge_context:
            full_system_prompt += knowledge_context

        # 构建消息列表
        messages = []
        if full_system_prompt:
            messages.append(SystemMessage(content=full_system_prompt))

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
            # 调用 create_agent 执行（自动处理 tool-calling 循环）
            result = await self.agent.ainvoke({"messages": messages})

            # 提取最终答案
            final_messages = result.get("messages", [])
            if not final_messages:
                raise ValueError("Agent returned no messages")

            last_message = final_messages[-1]
            content = last_message.content if hasattr(last_message, "content") else str(last_message)

            # 统计实际执行了多少个工具调用
            tool_call_count = sum(
                1 for msg in final_messages if isinstance(msg, ToolMessage)
            )
            action_taken = f"执行了 {tool_call_count} 个工具操作" if tool_call_count > 0 else None

            # 逐字符流式输出
            for char in content:
                yield {"type": "content", "content": char}

            yield {
                "type": "done",
                "content": AgentResponse(
                    content=content,
                    agent_type=self.agent_type,
                    action_taken=action_taken
                )
            }

        except Exception as e:
            yield {"type": "error", "content": str(e)}

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