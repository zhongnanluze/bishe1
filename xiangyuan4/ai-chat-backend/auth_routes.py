"""
用户认证路由
包含：注册、登录、Token 刷新、用户信息管理等 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from database import get_db, User
from auth_models import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenRefreshRequest,
    PasswordChangeRequest,
    PasswordResetRequest,
    TokenResponse,
    UserInfoResponse,
    UserProfileUpdateRequest,
    AuthResponse,
    CurrentUser
)
from auth_utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    refresh_access_token,
    authenticate_user,
    update_last_login,
    get_current_user,
    get_current_active_user,
    get_current_admin_user
)

router = APIRouter(prefix="/api/auth", tags=["认证"])
security = HTTPBearer()


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册
    
    - **username**: 用户名（3-50字符，只能包含字母、数字和下划线）
    - **email**: 邮箱地址
    - **password**: 密码（至少6位）
    - **student_id**: 学号（可选）
    - **full_name**: 真实姓名（可选）
    """
    try:
        # 检查用户名是否已存在
        result = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已被注册"
            )
        
        # 检查邮箱是否已存在
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
        
        # 检查学号是否已存在（如果提供）
        if user_data.student_id:
            result = await db.execute(
                select(User).where(User.student_id == user_data.student_id)
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="学号已被注册"
                )
        
        # 创建新用户
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            student_id=user_data.student_id if user_data.student_id else None,
            full_name=user_data.full_name if user_data.full_name else None,
            is_active=True,
            is_admin=False
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # 生成 Token
        access_token = create_access_token(new_user.id, new_user.username)
        refresh_token = create_refresh_token(new_user.id)
        
        return AuthResponse(
            success=True,
            message="注册成功",
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": {
                    "id": new_user.id,
                    "username": new_user.username,
                    "email": new_user.email,
                    "student_id": new_user.student_id,
                    "full_name": new_user.full_name
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败：{str(e)}"
        )


@router.post("/easy-login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def easy_login(
    login_data: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    免密快捷登录（仅开发测试使用）
    
    - **username**: 用户名或邮箱
    
    根据用户名直接返回Token，跳过密码校验
    """
    try:
        # 支持用户名或邮箱登录
        result = await db.execute(
            select(User).where(
                (User.username == login_data.username) | (User.email == login_data.username)
            )
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户账号已被禁用"
            )
        
        # 更新最后登录时间
        await update_last_login(user.id, db)
        
        # 生成 Token
        access_token = create_access_token(user.id, user.username)
        refresh_token = create_refresh_token(user.id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=30 * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"快捷登录失败：{str(e)}"
        )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    login_data: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    
    - **username**: 用户名或邮箱
    - **password**: 密码
    
    返回访问令牌和刷新令牌
    """
    try:
        # 验证用户凭据
        user = await authenticate_user(login_data.username, login_data.password, db)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 检查用户是否激活
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户账号已被禁用"
            )
        
        # 更新最后登录时间
        await update_last_login(user.id, db)
        
        # 生成 Token
        access_token = create_access_token(user.id, user.username)
        refresh_token = create_refresh_token(user.id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=30 * 60  # 30分钟
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败：{str(e)}"
        )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    刷新访问令牌
    
    - **refresh_token**: 刷新令牌
    
    返回新的访问令牌和刷新令牌
    """
    try:
        result = await refresh_access_token(refresh_data.refresh_token)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刷新令牌失败：{str(e)}"
        )


@router.get("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户信息
    
    需要认证：Bearer Token
    """
    return UserInfoResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        student_id=current_user.student_id,
        full_name=current_user.full_name,
        avatar=getattr(current_user, 'avatar', None),
        is_active=current_user.is_active,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.put("/me", response_model=UserInfoResponse, status_code=status.HTTP_200_OK)
async def update_user_profile(
    profile_data: UserProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新当前用户资料
    
    需要认证：Bearer Token
    
    - **username**: 用户名（可选）
    - **full_name**: 真实姓名（可选）
    - **email**: 邮箱（可选）
    - **student_id**: 学号（可选）
    """
    try:
        # 检查用户名是否被其他用户使用
        if profile_data.username and profile_data.username != current_user.username:
            result = await db.execute(
                select(User).where(
                    (User.username == profile_data.username) & 
                    (User.id != current_user.id)
                )
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已被其他用户使用"
                )
        
        # 检查邮箱是否被其他用户使用
        if profile_data.email and profile_data.email != current_user.email:
            result = await db.execute(
                select(User).where(
                    (User.email == profile_data.email) & 
                    (User.id != current_user.id)
                )
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被其他用户使用"
                )
        
        # 检查学号是否被其他用户使用
        if profile_data.student_id and profile_data.student_id != current_user.student_id:
            result = await db.execute(
                select(User).where(
                    (User.student_id == profile_data.student_id) & 
                    (User.id != current_user.id)
                )
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="学号已被其他用户使用"
                )
        
        # 更新用户信息
        update_data = {}
        if profile_data.username is not None:
            update_data["username"] = profile_data.username
        if profile_data.full_name is not None:
            update_data["full_name"] = profile_data.full_name
        if profile_data.email is not None:
            update_data["email"] = profile_data.email
        if profile_data.student_id is not None:
            update_data["student_id"] = profile_data.student_id
        if profile_data.avatar is not None:
            update_data["avatar"] = profile_data.avatar
        
        if update_data:
            await db.execute(
                update(User)
                .where(User.id == current_user.id)
                .values(**update_data)
            )
            await db.commit()
            # 重新从数据库中查询用户信息
            result = await db.execute(select(User).where(User.id == current_user.id))
            updated_user = result.scalar_one_or_none()
        else:
            # 如果没有更新数据，使用当前用户信息
            updated_user = None
        
        # 构建响应数据
        user_data = updated_user or current_user
        
        return UserInfoResponse(
            id=user_data.id,
            username=user_data.username,
            email=user_data.email,
            student_id=user_data.student_id,
            full_name=user_data.full_name,
            avatar=getattr(user_data, 'avatar', None),
            is_active=user_data.is_active,
            is_admin=user_data.is_admin,
            created_at=getattr(user_data, 'created_at', None),
            last_login=getattr(user_data, 'last_login', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新用户资料失败：{str(e)}"
        )


@router.post("/change-password", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    修改密码
    
    需要认证：Bearer Token
    
    - **old_password**: 旧密码
    - **new_password**: 新密码（至少6位）
    """
    try:
        # 从数据库中查询用户对象
        result = await db.execute(select(User).where(User.id == current_user.id))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 验证旧密码
        if not verify_password(password_data.old_password, db_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="旧密码错误"
            )
        
        # 检查新旧密码是否相同
        if verify_password(password_data.new_password, db_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="新密码不能与旧密码相同"
            )
        
        # 更新密码
        await db.execute(
            update(User)
            .where(User.id == current_user.id)
            .values(password_hash=get_password_hash(password_data.new_password))
        )
        await db.commit()
        
        return AuthResponse(
            success=True,
            message="密码修改成功",
            data=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改密码失败：{str(e)}"
        )


@router.post("/reset-password", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    重置密码（通过邮箱）
    
    - **email**: 注册邮箱
    
    注意：这是一个简化版本，实际应用中应该发送邮件验证
    """
    try:
        # 查找用户
        result = await db.execute(
            select(User).where(User.email == reset_data.email)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            # 为了安全，不暴露用户是否存在
            return AuthResponse(
                success=True,
                message="如果该邮箱已注册，重置链接已发送",
                data=None
            )
        
        # 这里应该生成重置令牌并发送邮件
        # 简化版本：直接重置为一个临时密码
        import secrets
        temp_password = secrets.token_urlsafe(12)
        
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(password_hash=get_password_hash(temp_password))
        )
        await db.commit()
        
        # 实际应用中，这里应该发送邮件
        # 简化版本：在响应中返回临时密码（仅用于演示）
        return AuthResponse(
            success=True,
            message=f"密码已重置，临时密码：{temp_password}（请尽快修改密码）",
            data={"temp_password": temp_password}
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置密码失败：{str(e)}"
        )


@router.post("/logout", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    用户登出
    
    需要认证：Bearer Token
    
    注意：由于 JWT 是无状态的，服务端无法直接使 Token 失效
    客户端应该删除本地存储的 Token
    """
    return AuthResponse(
        success=True,
        message="登出成功",
        data=None
    )


@router.get("/users", status_code=status.HTTP_200_OK)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户列表（仅管理员）
    
    需要认证：Bearer Token + 管理员权限
    
    - **skip**: 跳过记录数
    - **limit**: 返回记录数
    """
    try:
        result = await db.execute(
            select(User).offset(skip).limit(limit)
        )
        users = result.scalars().all()
        
        return {
            "total": len(users),
            "users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "student_id": user.student_id,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
                for user in users
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户列表失败：{str(e)}"
        )


@router.delete("/users/{user_id}", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除用户（仅管理员）
    
    需要认证：Bearer Token + 管理员权限
    
    - **user_id**: 用户ID
    """
    try:
        # 不能删除自己
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除自己"
            )
        
        # 查找用户
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 删除用户
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False)
        )
        await db.commit()
        
        return AuthResponse(
            success=True,
            message="用户已禁用",
            data={"user_id": user_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除用户失败：{str(e)}"
        )
