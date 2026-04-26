"""
数据库连接模块
使用 SQLAlchemy + aiomysql 实现异步 MySQL 操作
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.dialects.mysql import LONGTEXT
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "ai_chat_db")

# 构建数据库 URL（使用 aiomysql 驱动）
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 生产环境设为 False
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True  # 自动检测连接是否有效
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# 声明基类
Base = declarative_base()


# ============ 数据表模型 ============

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    student_id = Column(String(20), unique=True, nullable=True, comment="学号")
    full_name = Column(String(50), nullable=True, comment="真实姓名")
    avatar = Column(LONGTEXT, nullable=True, comment="头像Base64或URL")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_admin = Column(Boolean, default=False, comment="是否管理员")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    last_login = Column(DateTime, nullable=True, comment="最后登录时间")
    jwxt_username = Column(String(50), nullable=True, comment="教务系统账号")
    jwxt_password = Column(String(255), nullable=True, comment="教务系统密码")


class SessionModel(Base):
    """会话表（替换原有的内存存储）"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="会话ID")
    session_id = Column(String(100), unique=True, nullable=False, comment="会话标识")
    user_id = Column(Integer, nullable=True, comment="关联用户ID")
    topic = Column(String(255), nullable=True, comment="对话主题")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    last_active = Column(DateTime, default=datetime.now, comment="最后活跃时间")
    expires_at = Column(DateTime, nullable=False, comment="过期时间")
    is_active = Column(Boolean, default=True, comment="是否有效")


class ChatHistory(Base):
    """聊天记录表"""
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    session_id = Column(String(100), nullable=False, index=True, comment="会话ID")
    user_id = Column(Integer, nullable=True, comment="用户ID")
    role = Column(String(20), nullable=False, comment="角色：user/assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    agent_type = Column(String(50), nullable=True, comment="智能体类型")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


class KnowledgeBaseModel(Base):
    """知识库表"""
    __tablename__ = "knowledge_base"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="知识ID")
    title = Column(String(255), nullable=False, comment="知识标题")
    content = Column(Text, nullable=False, comment="知识内容")
    category = Column(String(100), nullable=True, comment="知识分类")
    agent_type = Column(String(50), nullable=True, comment="所属智能体类型：academic/student_services/psychology/policy/chat")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")


class UsageLog(Base):
    """API调用用量统计表"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    user_id = Column(Integer, nullable=True, comment="用户ID")
    session_id = Column(String(100), nullable=True, comment="会话ID")
    agent_type = Column(String(50), nullable=False, comment="智能体类型")
    prompt_tokens = Column(Integer, default=0, comment="Prompt token数")
    completion_tokens = Column(Integer, default=0, comment="Completion token数")
    total_tokens = Column(Integer, default=0, comment="总token数")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")


# ============ 数据库操作辅助函数 ============

async def get_db():
    """获取数据库会话（用于依赖注入）"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建所有表）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully")


async def drop_db():
    """删除所有表（谨慎使用）"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("⚠️ 数据库表已删除")
