"""
管理员统计路由
提供：用量统计、智能体调用统计、用户统计等可视化数据
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from sqlalchemy.dialects.mysql import DATETIME
from typing import Optional
from datetime import datetime, timedelta

from database import get_db, UsageLog, ChatHistory, User
from auth_utils import get_current_admin_user
from auth_models import CurrentUser

router = APIRouter(prefix="/api/admin", tags=["管理员统计"])


@router.get("/stats/overview")
async def get_overview_stats(
    current_user: CurrentUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """获取概览统计数据"""
    try:
        # 总调用次数
        total_calls_result = await db.execute(select(func.count(UsageLog.id)))
        total_calls = total_calls_result.scalar() or 0
        
        # 总token数
        total_tokens_result = await db.execute(select(func.sum(UsageLog.total_tokens)))
        total_tokens = total_tokens_result.scalar() or 0
        
        # 活跃用户数（有调用记录的用户）
        active_users_result = await db.execute(
            select(func.count(func.distinct(UsageLog.user_id))).where(UsageLog.user_id.isnot(None))
        )
        active_users = active_users_result.scalar() or 0
        
        # 今日调用数
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_calls_result = await db.execute(
            select(func.count(UsageLog.id)).where(UsageLog.created_at >= today)
        )
        today_calls = today_calls_result.scalar() or 0
        
        # 今日token数
        today_tokens_result = await db.execute(
            select(func.sum(UsageLog.total_tokens)).where(UsageLog.created_at >= today)
        )
        today_tokens = today_tokens_result.scalar() or 0
        
        # 总用户数
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar() or 0
        
        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "active_users": active_users,
            "total_users": total_users,
            "today_calls": today_calls,
            "today_tokens": today_tokens or 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概览统计失败: {str(e)}")


@router.get("/stats/by-user")
async def get_user_stats(
    days: int = 30,
    current_user: CurrentUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """按用户统计调用次数和token用量"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        # 按用户统计
        result = await db.execute(
            select(
                User.id,
                User.username,
                User.full_name,
                func.count(UsageLog.id).label("call_count"),
                func.sum(UsageLog.total_tokens).label("total_tokens"),
                func.sum(UsageLog.prompt_tokens).label("prompt_tokens"),
                func.sum(UsageLog.completion_tokens).label("completion_tokens")
            )
            .outerjoin(UsageLog, and_(UsageLog.user_id == User.id, UsageLog.created_at >= start_date))
            .group_by(User.id)
            .order_by(func.count(UsageLog.id).desc())
        )
        
        rows = result.all()
        return {
            "days": days,
            "users": [
                {
                    "id": row.id,
                    "username": row.username,
                    "full_name": row.full_name,
                    "call_count": row.call_count or 0,
                    "total_tokens": int(row.total_tokens or 0),
                    "prompt_tokens": int(row.prompt_tokens or 0),
                    "completion_tokens": int(row.completion_tokens or 0)
                }
                for row in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户统计失败: {str(e)}")


@router.get("/stats/by-agent")
async def get_agent_stats(
    days: int = 30,
    current_user: CurrentUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """按智能体统计调用次数"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(
                UsageLog.agent_type,
                func.count(UsageLog.id).label("call_count"),
                func.sum(UsageLog.total_tokens).label("total_tokens")
            )
            .where(UsageLog.created_at >= start_date)
            .group_by(UsageLog.agent_type)
            .order_by(func.count(UsageLog.id).desc())
        )
        
        rows = result.all()
        return {
            "days": days,
            "agents": [
                {
                    "agent_type": row.agent_type,
                    "call_count": row.call_count or 0,
                    "total_tokens": int(row.total_tokens or 0)
                }
                for row in rows
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取智能体统计失败: {str(e)}")


@router.get("/stats/trend")
async def get_trend_stats(
    days: int = 14,
    current_user: CurrentUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """获取时间趋势统计（每日调用次数和token数）"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        # 按日期统计
        result = await db.execute(
            select(
                func.date(UsageLog.created_at).label("date"),
                func.count(UsageLog.id).label("call_count"),
                func.sum(UsageLog.total_tokens).label("total_tokens")
            )
            .where(UsageLog.created_at >= start_date)
            .group_by(func.date(UsageLog.created_at))
            .order_by(func.date(UsageLog.created_at))
        )
        
        rows = result.all()
        
        # 填充没有数据的日期
        date_map = {str(row.date): {"call_count": row.call_count or 0, "total_tokens": int(row.total_tokens or 0)} for row in rows}
        
        dates = []
        call_counts = []
        token_counts = []
        
        for i in range(days, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            dates.append(d)
            call_counts.append(date_map.get(d, {}).get("call_count", 0))
            token_counts.append(date_map.get(d, {}).get("total_tokens", 0))
        
        return {
            "days": days,
            "dates": dates,
            "call_counts": call_counts,
            "token_counts": token_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取趋势统计失败: {str(e)}")


@router.get("/stats/agent-trend")
async def get_agent_trend_stats(
    days: int = 14,
    current_user: CurrentUser = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """获取各智能体的时间趋势"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(
                func.date(UsageLog.created_at).label("date"),
                UsageLog.agent_type,
                func.count(UsageLog.id).label("call_count")
            )
            .where(UsageLog.created_at >= start_date)
            .group_by(func.date(UsageLog.created_at), UsageLog.agent_type)
            .order_by(func.date(UsageLog.created_at))
        )
        
        rows = result.all()
        
        # 构建数据结构
        dates = []
        for i in range(days, -1, -1):
            dates.append((datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"))
        
        agent_types = ["academic", "student_services", "psychology", "policy", "chat"]
        agent_data = {agent: [0] * len(dates) for agent in agent_types}
        
        date_index = {d: i for i, d in enumerate(dates)}
        
        for row in rows:
            d = str(row.date)
            if d in date_index and row.agent_type in agent_data:
                agent_data[row.agent_type][date_index[d]] = row.call_count or 0
        
        return {
            "days": days,
            "dates": dates,
            "agents": [
                {
                    "agent_type": agent,
                    "call_counts": agent_data[agent]
                }
                for agent in agent_types
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取智能体趋势失败: {str(e)}")
