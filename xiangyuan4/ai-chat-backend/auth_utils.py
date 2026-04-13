"""
认证工具模块
包含：密码哈希、Token生成/验证、用户认证等工具函数
"""

from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db, User
from auth_models import TokenPayload, CurrentUser

# ============ 安全配置 ============

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = "your-secret-key-here-change-in-production"  # 生产环境应使用环境变量
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# HTTP Bearer 安全方案
security = HTTPBearer()


# ============ 密码工具函数 ============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
        
    Returns:
        bool: 验证结果
    """
    # 检查是否是 SHA256 哈希（来自 init_db.py）
    if hashed_password.startswith('$sha256$'):
        import hashlib
        expected_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        return hashed_password == f"$sha256${expected_hash}"
    # 否则使用 bcrypt 验证
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    获取密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        str: 密码哈希
    """
    # 使用 SHA256 哈希算法，避免 bcrypt 版本兼容性问题
    import hashlib
    return f"$sha256${hashlib.sha256(password.encode('utf-8')).hexdigest()}"


# ============ Token 工具函数 ============

def create_access_token(user_id: Union[int, str], username: str) -> str:
    """
    创建访问令牌
    
    Args:
        user_id: 用户ID
        username: 用户名
        
    Returns:
        str: JWT Token
    """
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
        "username": username
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: Union[int, str]) -> str:
    """
    创建刷新令牌
    
    Args:
        user_id: 用户ID
        
    Returns:
        str: JWT Refresh Token
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenPayload]:
    """
    解码并验证 Token
    
    Args:
        token: JWT Token
        
    Returns:
        TokenPayload: Token 载荷，验证失败返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # 验证必要字段
        user_id = payload.get("sub")
        token_type = payload.get("type")
        
        if user_id is None or token_type is None:
            return None
        
        return TokenPayload(
            sub=user_id,
            exp=datetime.fromtimestamp(payload.get("exp")),
            iat=datetime.fromtimestamp(payload.get("iat")),
            type=token_type,
            username=payload.get("username")
        )
    except JWTError:
        return None


async def refresh_access_token(refresh_token: str) -> Optional[dict]:
    """
    使用刷新令牌获取新的访问令牌
    
    Args:
        refresh_token: 刷新令牌
        
    Returns:
        Optional[dict]: 包含新的访问令牌和刷新令牌的字典，失败返回 None
    """
    payload = decode_token(refresh_token)
    
    if payload is None or payload.type != "refresh":
        return None
    
    # 创建新的访问令牌和刷新令牌
    access_token = create_access_token(payload.sub, payload.username or "")
    new_refresh_token = create_refresh_token(payload.sub)
    
    # 返回符合 TokenResponse 模型的字典
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 30 * 60  # 30分钟
    }


# ============ 用户认证依赖 ============

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[CurrentUser]:
    """
    获取当前登录用户（依赖注入）
    
    使用方式：
        @app.get("/protected")
        async def protected_route(current_user: CurrentUser = Depends(get_current_user)):
            return {"message": f"Hello {current_user.username}"}
    
    Args:
        credentials: HTTP 认证凭证（可选）
        db: 数据库会话
        
    Returns:
        CurrentUser: 当前用户信息，如果未登录则返回 None
    """
    if not credentials:
        return None
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 解码 Token
    token_payload = decode_token(credentials.credentials)
    
    if token_payload is None:
        return None
    
    # 验证 Token 类型
    if token_payload.type != "access":
        return None
    
    # 查询用户
    try:
        user_id = int(token_payload.sub)
    except ValueError:
        return None
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        return None
    
    if not user.is_active:
        return None
    
    return CurrentUser(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        student_id=user.student_id,
        full_name=user.full_name,
        avatar=getattr(user, 'avatar', None),
        created_at=user.created_at,
        last_login=user.last_login
    )


async def get_current_active_user(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    获取当前活跃用户（确保用户已激活）
    
    Args:
        current_user: 当前用户
        
    Returns:
        CurrentUser: 当前用户信息
        
    Raises:
        HTTPException: 用户未激活或未登录
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号未激活"
        )
    return current_user


async def get_current_admin_user(
    current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """
    获取当前管理员用户
    
    Args:
        current_user: 当前用户
        
    Returns:
        CurrentUser: 当前管理员用户信息
        
    Raises:
        HTTPException: 用户不是管理员
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


# ============ 用户认证函数 ============

async def authenticate_user(
    username: str,
    password: str,
    db: AsyncSession
) -> Optional[User]:
    """
    验证用户凭据
    
    Args:
        username: 用户名或邮箱
        password: 密码
        db: 数据库会话
        
    Returns:
        Optional[User]: 验证成功返回用户对象，失败返回 None
    """
    # 支持用户名或邮箱登录
    result = await db.execute(
        select(User).where(
            (User.username == username) | (User.email == username)
        )
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user


async def update_last_login(user_id: int, db: AsyncSession) -> None:
    """
    更新用户最后登录时间
    
    Args:
        user_id: 用户ID
        db: 数据库会话
    """
    from sqlalchemy import update
    await db.execute(
        update(User).where(User.id == user_id).values(
            last_login=datetime.utcnow()
        )
    )
    await db.commit()
