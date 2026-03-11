"""
会话管理模块
管理用户会话和对话历史
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid
import asyncio


@dataclass
class Session:
    """会话数据结构"""
    session_id: str
    created_at: datetime
    last_active: datetime
    conversation_history: List[Dict] = field(default_factory=list)
    current_agent: Optional[str] = None
    context: Dict = field(default_factory=dict)


class SessionManager:
    """
    会话管理器
    负责创建、管理和清理用户会话
    """
    
    def __init__(self, session_timeout: int = 3600):
        """
        初始化会话管理器
        
        Args:
            session_timeout: 会话超时时间（秒），默认1小时
        """
        self.sessions: Dict[str, Session] = {}
        self.session_timeout = session_timeout
        self._lock = asyncio.Lock()
    
    async def create_session(self) -> str:
        """
        创建新会话
        
        Returns:
            str: 会话ID
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        async with self._lock:
            self.sessions[session_id] = Session(
                session_id=session_id,
                created_at=now,
                last_active=now,
                conversation_history=[],
                current_agent=None,
                context={}
            )
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Session: 会话对象，不存在则返回None
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                # 更新最后活动时间
                session.last_active = datetime.now()
            return session
    
    async def add_message(self, session_id: str, role: str, content: str, agent_type: str = None):
        """
        添加对话消息
        
        Args:
            session_id: 会话ID
            role: 角色（user/assistant）
            content: 消息内容
            agent_type: 智能体类型（可选）
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                message = {
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
                if agent_type:
                    message["agent_type"] = agent_type
                    session.current_agent = agent_type
                
                session.conversation_history.append(message)
                session.last_active = datetime.now()
                
                # 限制历史记录长度，保留最近20轮
                if len(session.conversation_history) > 40:
                    session.conversation_history = session.conversation_history[-40:]
    
    async def get_conversation_history(self, session_id: str) -> List[Dict]:
        """
        获取对话历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict]: 对话历史列表
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                return session.conversation_history.copy()
            return []
    
    async def update_context(self, session_id: str, key: str, value: any):
        """
        更新会话上下文
        
        Args:
            session_id: 会话ID
            key: 上下文键
            value: 上下文值
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session.context[key] = value
                session.last_active = datetime.now()
    
    async def get_context(self, session_id: str, key: str = None) -> any:
        """
        获取会话上下文
        
        Args:
            session_id: 会话ID
            key: 上下文键，为None则返回全部上下文
            
        Returns:
            any: 上下文值
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if session:
                if key is None:
                    return session.context.copy()
                return session.context.get(key)
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否删除成功
        """
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    async def cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.now()
        expired_sessions = []
        
        async with self._lock:
            for session_id, session in self.sessions.items():
                if now - session.last_active > timedelta(seconds=self.session_timeout):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.sessions[session_id]
        
        return len(expired_sessions)
    
    async def get_session_stats(self) -> Dict:
        """
        获取会话统计信息
        
        Returns:
            Dict: 统计信息
        """
        async with self._lock:
            total_sessions = len(self.sessions)
            active_sessions = sum(
                1 for s in self.sessions.values()
                if datetime.now() - s.last_active < timedelta(minutes=5)
            )
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "session_timeout": self.session_timeout
            }


# 全局会话管理器实例
session_manager = SessionManager()
