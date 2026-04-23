"""
会话管理模块
管理用户会话和对话历史
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_

# 导入数据库模型
from database import SessionModel, ChatHistory, AsyncSessionLocal


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
        self.session_timeout = session_timeout
        self._lock = asyncio.Lock()
    
    async def _get_db(self) -> AsyncSession:
        """获取数据库会话"""
        async with AsyncSessionLocal() as session:
            return session
    
    async def create_session(self, user_id: Optional[int] = None, topic: Optional[str] = None, user_info: Optional[dict] = None) -> str:
        """
        创建新会话
        
        Args:
            user_id: 用户ID（可选）
            topic: 对话主题（可选）
            user_info: 用户信息（可选，包含姓名、学号等）
            
        Returns:
            str: 会话ID
        """
        session_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.session_timeout)
        
        async with AsyncSessionLocal() as db:
            try:
                # 创建会话记录
                new_session = SessionModel(
                    session_id=session_id,
                    user_id=user_id,
                    topic=topic,
                    created_at=now,
                    last_active=now,
                    expires_at=expires_at,
                    is_active=True
                )
                db.add(new_session)
                await db.commit()
                await db.refresh(new_session)
                
                # 生成个性化欢迎消息
                welcome_message = "你好！我是学生智能服务助手，有什么可以帮助你的吗？"
                if user_info:
                    full_name = user_info.get("full_name") or user_info.get("username")
                    student_id = user_info.get("student_id")
                    if full_name:
                        welcome_message = f"你好！{full_name}"
                        if student_id:
                            welcome_message += f"（学号：{student_id}）"
                        welcome_message += "，我是学生智能服务助手，有什么可以帮助你的吗？"
                
                # 添加欢迎消息到数据库
                new_chat = ChatHistory(
                    session_id=session_id,
                    user_id=user_id,
                    role='assistant',
                    content=welcome_message,
                    agent_type='chat'
                )
                db.add(new_chat)
                await db.commit()
            except Exception as e:
                await db.rollback()
                raise e
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话信息
        
        Args:
            session_id: 会话ID
            
        Returns:
            Session: 会话对象，不存在则返回None
        """
        async with AsyncSessionLocal() as db:
            # 查询会话记录，只检查session_id和is_active，不检查是否过期
            # 这样用户可以查看历史对话记录
            result = await db.execute(
                select(SessionModel).where(
                    and_(
                        SessionModel.session_id == session_id,
                        SessionModel.is_active == True
                    )
                )
            )
            session_model = result.scalar_one_or_none()
            
            if not session_model:
                return None
            
            # 更新最后活动时间和过期时间
            session_model.last_active = datetime.now()
            session_model.expires_at = datetime.now() + timedelta(seconds=self.session_timeout)
            await db.commit()
            
            # 获取对话历史
            history_result = await db.execute(
                select(ChatHistory).where(
                    ChatHistory.session_id == session_id
                ).order_by(ChatHistory.created_at)
            )
            chat_history = history_result.scalars().all()
            
            # 构建会话对象
            conversation_history = []
            current_agent = None
            
            for chat in chat_history:
                message = {
                    "role": chat.role,
                    "content": chat.content,
                    "timestamp": chat.created_at.isoformat()
                }
                if chat.agent_type:
                    message["agent_type"] = chat.agent_type
                    current_agent = chat.agent_type
                conversation_history.append(message)
            
            return Session(
                session_id=session_model.session_id,
                created_at=session_model.created_at,
                last_active=session_model.last_active,
                conversation_history=conversation_history,
                current_agent=current_agent,
                context={}
            )
    
    async def add_message(self, session_id: str, role: str, content: str, agent_type: str = None):
        """
        添加对话消息
        
        Args:
            session_id: 会话ID
            role: 角色（user/assistant）
            content: 消息内容
            agent_type: 智能体类型（可选）
        """
        async with AsyncSessionLocal() as db:
            try:
                # 检查会话是否存在
                result = await db.execute(
                    select(SessionModel).where(
                        and_(
                            SessionModel.session_id == session_id,
                            SessionModel.is_active == True
                        )
                    )
                )
                session_model = result.scalar_one_or_none()
                
                if not session_model:
                    return
                
                # 更新会话的最后活动时间
                session_model.last_active = datetime.now()
                session_model.expires_at = datetime.now() + timedelta(seconds=self.session_timeout)
                
                # 检查是否是第一条消息，如果是且角色是用户，则生成对话主题
                if role == 'user' and not session_model.topic:
                    # 生成对话主题：取消息的前20个字符作为主题
                    topic = content.strip()[:20]
                    if len(topic) > 15:
                        topic = topic[:15] + '...'
                    session_model.topic = topic
                
                # 创建聊天记录
                new_chat = ChatHistory(
                    session_id=session_id,
                    user_id=session_model.user_id,
                    role=role,
                    content=content,
                    agent_type=agent_type
                )
                db.add(new_chat)
                
                # 限制历史记录长度，保留最近20轮（40条消息）
                history_result = await db.execute(
                    select(ChatHistory).where(
                        ChatHistory.session_id == session_id
                    ).order_by(ChatHistory.created_at.desc())
                )
                all_chats = history_result.scalars().all()
                
                if len(all_chats) > 40:
                    chats_to_delete = all_chats[40:]
                    for chat in chats_to_delete:
                        await db.delete(chat)
                
                await db.commit()
            except Exception as e:
                await db.rollback()
                raise e
    
    async def get_conversation_history(self, session_id: str) -> List[Dict]:
        """
        获取对话历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict]: 对话历史列表
        """
        async with AsyncSessionLocal() as db:
            # 检查会话是否存在，只检查session_id和is_active，不检查是否过期
            # 这样用户可以查看历史对话记录
            result = await db.execute(
                select(SessionModel).where(
                    and_(
                        SessionModel.session_id == session_id,
                        SessionModel.is_active == True
                    )
                )
            )
            session_model = result.scalar_one_or_none()
            
            if not session_model:
                return []
            
            # 获取对话历史
            history_result = await db.execute(
                select(ChatHistory).where(
                    ChatHistory.session_id == session_id
                ).order_by(ChatHistory.created_at)
            )
            chat_history = history_result.scalars().all()
            
            # 构建对话历史列表
            conversation_history = []
            for chat in chat_history:
                message = {
                    "role": chat.role,
                    "content": chat.content,
                    "timestamp": chat.created_at.isoformat()
                }
                if chat.agent_type:
                    message["agent_type"] = chat.agent_type
                conversation_history.append(message)
            
            return conversation_history
    
    async def update_context(self, session_id: str, key: str, value: any):
        """
        更新会话上下文
        
        Args:
            session_id: 会话ID
            key: 上下文键
            value: 上下文值
        """
        # 上下文暂时存储在内存中，后续可以考虑添加到数据库表
        pass
    
    async def get_context(self, session_id: str, key: str = None) -> any:
        """
        获取会话上下文
        
        Args:
            session_id: 会话ID
            key: 上下文键，为None则返回全部上下文
            
        Returns:
            any: 上下文值
        """
        # 上下文暂时存储在内存中，后续可以考虑添加到数据库表
        return None
    
    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否删除成功
        """
        # 验证会话ID
        if not session_id or not isinstance(session_id, str):
            return False
        
        async with AsyncSessionLocal() as db:
            try:
                # 检查会话是否存在
                result = await db.execute(
                    select(SessionModel).where(
                        SessionModel.session_id == session_id
                    )
                )
                session_model = result.scalar_one_or_none()
                
                if not session_model:
                    return False
                
                # 软删除会话
                session_model.is_active = False
                session_model.expires_at = datetime.now()
                await db.commit()
                
                return True
            except Exception as e:
                await db.rollback()
                return False
    
    async def cleanup_expired_sessions(self):
        """清理过期会话"""
        async with AsyncSessionLocal() as db:
            try:
                # 查找过期会话
                now = datetime.now()
                result = await db.execute(
                    select(SessionModel).where(
                        and_(
                            SessionModel.is_active == True,
                            SessionModel.expires_at <= now
                        )
                    )
                )
                expired_sessions = result.scalars().all()
                
                # 软删除过期会话
                for session in expired_sessions:
                    session.is_active = False
                
                if expired_sessions:
                    await db.commit()
                
                return len(expired_sessions)
            except Exception as e:
                await db.rollback()
                return 0
    
    async def get_session_stats(self) -> Dict:
        """
        获取会话统计信息
        
        Returns:
            Dict: 统计信息
        """
        async with AsyncSessionLocal() as db:
            # 获取总会话数
            total_result = await db.execute(
                select(SessionModel).where(
                    SessionModel.is_active == True
                )
            )
            total_sessions = len(total_result.scalars().all())
            
            # 获取活跃会话数（5分钟内有活动）
            now = datetime.now()
            active_result = await db.execute(
                select(SessionModel).where(
                    and_(
                        SessionModel.is_active == True,
                        SessionModel.last_active >= now - timedelta(minutes=5)
                    )
                )
            )
            active_sessions = len(active_result.scalars().all())
            
            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "session_timeout": self.session_timeout
            }
    
    async def get_user_sessions(self, user_id: int) -> List[Dict]:
        """
        获取用户的会话列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict]: 会话列表，包含会话ID、创建时间、最后活动时间、消息数量和当前智能体
        """
        async with AsyncSessionLocal() as db:
            # 查询用户的所有活跃会话
            result = await db.execute(
                select(SessionModel).where(
                    and_(
                        SessionModel.user_id == user_id,
                        SessionModel.is_active == True
                    )
                ).order_by(SessionModel.last_active.desc())
            )
            sessions = result.scalars().all()
            
            session_list = []
            for session in sessions:
                # 获取会话的消息数量
                message_count_result = await db.execute(
                    select(ChatHistory).where(
                        ChatHistory.session_id == session.session_id
                    )
                )
                message_count = len(message_count_result.scalars().all())
                
                # 获取最后一条消息的智能体类型
                last_message_result = await db.execute(
                    select(ChatHistory).where(
                        ChatHistory.session_id == session.session_id
                    ).order_by(ChatHistory.created_at.desc()).limit(1)
                )
                last_message = last_message_result.scalar_one_or_none()
                current_agent = last_message.agent_type if last_message else None
                
                session_list.append({
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "last_active": session.last_active.isoformat(),
                    "message_count": message_count,
                    "current_agent": current_agent,
                    "topic": session.topic
                })
            
            return session_list


# 全局会话管理器实例
session_manager = SessionManager()
