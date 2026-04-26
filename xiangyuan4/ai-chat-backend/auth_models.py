"""
认证相关数据模型
包含：用户请求/响应模型、Token模型等
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


# ============ 用户认证请求模型 ============

class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, description="密码")
    student_id: Optional[str] = Field(None, max_length=20, description="学号")
    full_name: Optional[str] = Field(None, max_length=50, description="真实姓名")


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class TokenRefreshRequest(BaseModel):
    """Token刷新请求"""
    refresh_token: str = Field(..., description="刷新令牌")


class PasswordChangeRequest(BaseModel):
    """密码修改请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


class PasswordResetRequest(BaseModel):
    """密码重置请求"""
    email: EmailStr = Field(..., description="邮箱")


# ============ 用户认证响应模型 ============

class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class UserInfoResponse(BaseModel):
    """用户信息响应"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    student_id: Optional[str] = Field(None, description="学号")
    full_name: Optional[str] = Field(None, description="真实姓名")
    avatar: Optional[str] = Field(None, description="头像URL")
    jwxt_username: Optional[str] = Field(None, description="教务系统账号")
    jwxt_password: Optional[str] = Field(None, description="教务系统密码")
    is_active: bool = Field(..., description="是否激活")
    is_admin: bool = Field(..., description="是否管理员")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    
    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """用户资料更新请求"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    full_name: Optional[str] = Field(None, max_length=50, description="真实姓名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    student_id: Optional[str] = Field(None, max_length=20, description="学号")
    avatar: Optional[str] = Field(None, description="头像URL")
    jwxt_username: Optional[str] = Field(None, max_length=50, description="教务系统账号")
    jwxt_password: Optional[str] = Field(None, max_length=255, description="教务系统密码")


class AuthResponse(BaseModel):
    """通用认证响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    data: Optional[dict] = Field(None, description="数据")


# ============ 内部使用模型 ============

class TokenPayload(BaseModel):
    """JWT Token 载荷"""
    sub: str = Field(..., description="主题（用户ID）")
    exp: datetime = Field(..., description="过期时间")
    iat: datetime = Field(..., description="签发时间")
    type: str = Field(..., description="Token 类型：access/refresh")
    username: Optional[str] = Field(None, description="用户名")


class CurrentUser(BaseModel):
    """当前登录用户信息（用于依赖注入）"""
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    is_active: bool = Field(..., description="是否激活")
    is_admin: bool = Field(..., description="是否管理员")
    student_id: Optional[str] = Field(None, description="学号")
    full_name: Optional[str] = Field(None, description="真实姓名")
    avatar: Optional[str] = Field(None, description="头像URL")
    jwxt_username: Optional[str] = Field(None, description="教务系统账号")
    jwxt_password: Optional[str] = Field(None, description="教务系统密码")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
