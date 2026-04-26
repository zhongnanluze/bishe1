"""
日常聊天智能体
处理：校园生活闲聊、一般性咨询、问候和寒暄
"""

from typing import Dict, Optional, AsyncGenerator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from .base_agent import BaseAgent, AgentResponse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env_utils import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from rag_service import RAGService


class ChatAgent(BaseAgent):
    """日常聊天智能体"""
    
    def __init__(self):
        super().__init__(
            name="日常聊天智能体",
            description="处理校园生活闲聊、一般性咨询、问候和寒暄"
        )
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.7,
            max_tokens=2048
        )
        self.rag_service = RAGService()

    async def _build_knowledge_context(self, query: str) -> str:
        """检索知识库并格式化上下文"""
        results = await self.rag_service.search(query, top_k=2, agent_type="chat")
        if not results:
            return ""
        context = "\n\n【知识库参考信息】\n"
        for r in results:
            snippet = r['content'][:400] + ('...' if len(r['content']) > 400 else '')
            context += f"· [{r['title']}] {snippet}\n"
        return context
    
    async def stream_process(self, message: str, session_id: str, context: Dict = None) -> AsyncGenerator[Dict, None]:
        """流式处理日常聊天请求"""
        
        system_prompt = """你是文泽奇妙小AI的日常聊天伙伴，一位活泼、幽默且亲切的校园朋友。你可以和学生轻松地聊任何话题，让校园生活变得更加有趣。

你的职责：
- 校园生活闲聊：美食推荐、活动资讯、天气提醒、趣事分享
- 一般性咨询：校园设施位置、周边信息、生活小贴士
- 问候与寒暄：热情回应用户的问候，主动关心
- 情绪陪伴：当用户只是想找人聊聊天时，做一个好的倾听者
- 学习之余的放松：讲笑话、推荐音乐/电影、分享正能量

服务风格：
- 语气轻松自然，像好朋友一样聊天
- 适当使用网络流行语和表情符号 😊
- 热情、积极、充满正能量
- 幽默风趣但不失分寸
- 乐于分享实用的校园生活小技巧

重要准则：
- 不涉及敏感政治话题
- 不提供有害、违法或不道德的建议
- 遇到超出能力范围的问题，友好地引导至相关智能体
- 当用户的问题明显属于学业、办事、心理或制度范畴时，可以简单回答后建议转接专业智能体
- 优先使用知识库中的校园生活信息
- 不要编造不确定的信息

记住：你的目标是让学生在繁忙的学习之余，感受到轻松和愉快！"""

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
            full_content = ""
            async for chunk in self.llm.astream(messages):
                content = chunk.content if hasattr(chunk, "content") else str(chunk)
                if content:
                    full_content += content
                    for char in content:
                        yield {"type": "content", "content": char}
            
            yield {
                "type": "done",
                "content": AgentResponse(
                    content=full_content,
                    agent_type="chat",
                    action_taken=None
                )
            }
            
        except Exception as e:
            error_message = f"哎呀，刚才走神了 😅 请再说一遍好吗？"
            yield {"type": "content", "content": error_message}
            yield {"type": "done", "content": AgentResponse(content=error_message, agent_type="chat", action_taken="error")}
