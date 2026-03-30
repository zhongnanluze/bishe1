"""
FastAPI Web 服务入口
提供多智能体对话 API（支持流式输出）
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, AsyncGenerator
import asyncio
import uvicorn
import json

# 导入智能体模块
from agents.router import AgentRouter, AgentType
from agents.student_affairs_agent import StudentAffairsAgent
from agents.academic_agent import AcademicAgent
from session_manager import session_manager

# 导入认证路由
from auth_routes import router as auth_router
from database import init_db

# 创建 FastAPI 应用
app = FastAPI(
    title="学生智能服务系统 API",
    description="支持学生事务和学业智能体的多智能体对话系统（支持流式输出）",
    version="1.0.0"
)

# 配置 CORS 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 请求/响应模型 ============

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    session_id: str
    agent_type: str
    action_taken: Optional[str] = None


class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str
    created_at: str
    last_active: str
    message_count: int
    current_agent: Optional[str]


# ============ 智能体实例 ============

# 初始化智能体
router = AgentRouter()
student_affairs_agent = StudentAffairsAgent()
academic_agent = AcademicAgent()

# 智能体映射表
AGENTS = {
    AgentType.STUDENT_AFFAIRS: student_affairs_agent,
    AgentType.ACADEMIC: academic_agent,
}


# ============ 流式输出辅助函数 ============

async def stream_response(
    message: str,
    session_id: str,
    agent_type: AgentType,
    conversation_history: list
) -> AsyncGenerator[str, None]:
    """
    流式生成响应
    
    Args:
        message: 用户消息
        session_id: 会话ID
        agent_type: 智能体类型
        conversation_history: 对话历史
        
    Yields:
        str: JSON格式的数据块
    """
    try:
        # 获取对应的智能体
        agent = AGENTS.get(agent_type)
        
        if not agent:
            # 通用回复
            response_content = "您好！我是学生智能服务助手。我可以帮您处理：\n\n1. **学生事务**：证件补办、学费缴纳、饭卡充值、办事流程查询\n2. **学业相关**：选课、课表查询、成绩查询、GPA计算\n\n请问有什么可以帮助您的？"
            agent_type_str = "general"
            action_taken = None
            
            # 流式输出通用回复（逐字）
            for i, char in enumerate(response_content):
                chunk = {
                    "type": "content",
                    "content": char,
                    "index": i,
                    "total": len(response_content)
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)  # 模拟打字效果
            
            # 发送完成信号
            end_chunk = {
                "type": "done",
                "agent_type": agent_type_str,
                "action_taken": action_taken
            }
            yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
        else:
            # 调用智能体处理请求
            agent_response = await agent.process(
                message=message,
                session_id=session_id,
                context={"history": conversation_history}
            )
            response_content = agent_response.content
            agent_type_str = agent_response.agent_type
            action_taken = agent_response.action_taken
            
            # 流式输出响应内容（逐字）
            for i, char in enumerate(response_content):
                chunk = {
                    "type": "content",
                    "content": char,
                    "index": i,
                    "total": len(response_content)
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)  # 模拟打字效果
            
            # 发送完成信号
            end_chunk = {
                "type": "done",
                "agent_type": agent_type_str,
                "action_taken": action_taken
            }
            yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
        
        # 保存对话历史
        await session_manager.add_message(session_id, "user", message)
        await session_manager.add_message(session_id, "assistant", response_content, agent_type_str)
        
    except Exception as e:
        error_chunk = {
            "type": "error",
            "error": str(e)
        }
        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"


# ============ API 端点 ============

@app.get("/")
async def root():
    """根路径 - 服务状态检查"""
    return {
        "status": "running",
        "service": "学生智能服务系统 API",
        "version": "1.0.0",
        "docs": "/docs",
        "streaming": "enabled"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    stats = await session_manager.get_session_stats()
    return {
        "status": "healthy",
        "sessions": stats
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    主要对话端点（非流式）
    
    接收用户消息，由系统自动路由到合适的智能体进行处理
    """
    try:
        # 1. 获取或创建会话
        session_id = request.session_id
        if not session_id:
            session_id = await session_manager.create_session()
        else:
            session = await session_manager.get_session(session_id)
            if not session:
                # 会话不存在，创建新会话
                session_id = await session_manager.create_session()
        
        # 2. 获取对话历史
        conversation_history = await session_manager.get_conversation_history(session_id)
        
        # 3. 路由决策 - 选择智能体
        agent_type = await router.route(request.message, conversation_history)
        
        # 4. 获取对应的智能体
        agent = AGENTS.get(agent_type)
        
        if not agent:
            # 如果没有匹配的智能体，使用通用回复
            response_content = "您好！我是学生智能服务助手。我可以帮您处理：\n\n1. **学生事务**：证件补办、学费缴纳、饭卡充值、办事流程查询\n2. **学业相关**：选课、课表查询、成绩查询、GPA计算\n\n请问有什么可以帮助您的？"
            agent_type_str = "general"
            action_taken = None
        else:
            # 5. 调用智能体处理请求
            agent_response = await agent.process(
                message=request.message,
                session_id=session_id,
                context={"history": conversation_history}
            )
            response_content = agent_response.content
            agent_type_str = agent_response.agent_type
            action_taken = agent_response.action_taken
        
        # 6. 保存对话历史
        await session_manager.add_message(session_id, "user", request.message)
        await session_manager.add_message(session_id, "assistant", response_content, agent_type_str)
        
        # 7. 返回响应
        return ChatResponse(
            response=response_content,
            session_id=session_id,
            agent_type=agent_type_str,
            action_taken=action_taken
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式对话端点（推荐使用）
    
    使用Server-Sent Events (SSE)实现流式输出
    """
    try:
        # 1. 获取或创建会话
        session_id = request.session_id
        if not session_id:
            session_id = await session_manager.create_session()
        else:
            session = await session_manager.get_session(session_id)
            if not session:
                # 会话不存在，创建新会话
                session_id = await session_manager.create_session()
        
        # 2. 获取对话历史
        conversation_history = await session_manager.get_conversation_history(session_id)
        
        # 3. 路由决策 - 选择智能体
        agent_type = await router.route(request.message, conversation_history)
        
        # 4. 返回流式响应
        return StreamingResponse(
            stream_response(
                message=request.message,
                session_id=session_id,
                agent_type=agent_type,
                conversation_history=conversation_history
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@app.post("/api/chat/direct/{agent_type}")
async def chat_direct(agent_type: str, request: ChatRequest):
    """
    直接指定智能体进行对话（非流式）
    
    Args:
        agent_type: 智能体类型 (student_affairs / academic)
    """
    try:
        # 获取或创建会话
        session_id = request.session_id
        if not session_id:
            session_id = await session_manager.create_session()
        
        # 根据类型选择智能体
        if agent_type == "student_affairs":
            agent = student_affairs_agent
            agent_type_enum = AgentType.STUDENT_AFFAIRS
        elif agent_type == "academic":
            agent = academic_agent
            agent_type_enum = AgentType.ACADEMIC
        else:
            raise HTTPException(status_code=400, detail=f"未知的智能体类型: {agent_type}")
        
        # 获取对话历史
        conversation_history = await session_manager.get_conversation_history(session_id)
        
        # 调用智能体
        agent_response = await agent.process(
            message=request.message,
            session_id=session_id,
            context={"history": conversation_history}
        )
        
        # 保存对话历史
        await session_manager.add_message(session_id, "user", request.message)
        await session_manager.add_message(session_id, "assistant", agent_response.content, agent_type)
        
        return ChatResponse(
            response=agent_response.content,
            session_id=session_id,
            agent_type=agent_type,
            action_taken=agent_response.action_taken
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    """获取会话信息"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return SessionInfo(
        session_id=session.session_id,
        created_at=session.created_at.isoformat(),
        last_active=session.last_active.isoformat(),
        message_count=len(session.conversation_history),
        current_agent=session.current_agent
    )


@app.get("/api/session/{session_id}/history")
async def get_session_history(session_id: str):
    """获取会话历史记录"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {
        "session_id": session_id,
        "history": session.conversation_history
    }


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    success = await session_manager.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return {"message": "会话已删除", "session_id": session_id}


@app.get("/api/agents")
async def list_agents():
    """列出所有可用的智能体"""
    return {
        "agents": [
            {
                "type": "student_affairs",
                "name": "学生事务智能体",
                "description": "处理证件补办、学费缴纳、饭卡充值、办事流程查询等",
                "capabilities": [
                    "证件补办（校园卡、学生证）",
                    "学费缴纳",
                    "饭卡充值",
                    "办事流程查询",
                    "学生事务中心信息"
                ]
            },
            {
                "type": "academic",
                "name": "学生学业智能体",
                "description": "处理选课、课表查询、成绩查询、学业规划等",
                "capabilities": [
                    "选课、退课",
                    "课表查询",
                    "成绩查询",
                    "GPA计算",
                    "学业日历",
                    "课程搜索"
                ]
            }
        ]
    }


# ============ 后台任务 ============

async def cleanup_task():
    """定期清理过期会话的后台任务"""
    while True:
        try:
            await asyncio.sleep(3600)  # 每小时执行一次
            cleaned = await session_manager.cleanup_expired_sessions()
            if cleaned > 0:
                print(f"清理了 {cleaned} 个过期会话")
        except Exception as e:
            print(f"清理任务出错: {e}")


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    # 初始化数据库
    await init_db()
    
    # 注册认证路由
    app.include_router(auth_router)
    
    # 启动后台清理任务
    asyncio.create_task(cleanup_task())
    print("=" * 50)
    print("学生智能服务系统 API 已启动")
    print("=" * 50)
    print("可用端点:")
    print("  - POST /api/auth/register  用户注册")
    print("  - POST /api/auth/login     用户登录")
    print("  - POST /api/auth/refresh   刷新Token")
    print("  - GET  /api/auth/me        获取用户信息")
    print("  - POST /api/chat          智能路由对话（非流式）")
    print("  - POST /api/chat/stream    智能路由对话（流式）")
    print("  - POST /api/chat/direct   指定智能体对话")
    print("  - GET  /api/agents        查看可用智能体")
    print("  - GET  /docs              API 文档")
    print("=" * 50)


# ============ 主入口 ============

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
