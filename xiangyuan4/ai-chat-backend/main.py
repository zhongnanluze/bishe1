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

# Token 计数（优先使用 tiktoken，未安装时回退到字符估算）
try:
    import tiktoken
    _tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
    TIKTOKEN_AVAILABLE = True
    print("[TokenCounter] tiktoken 已加载，使用 cl100k_base 编码")
except Exception:
    TIKTOKEN_AVAILABLE = False
    _tiktoken_encoder = None
    print("[TokenCounter] tiktoken 未安装，回退到字符估算")


def count_tokens(text: str) -> int:
    """计算文本的 token 数量"""
    if not text:
        return 0
    if TIKTOKEN_AVAILABLE and _tiktoken_encoder:
        return len(_tiktoken_encoder.encode(text))
    # Fallback: 中文字符约 1:1~1.5，取保守值
    return max(len(text), 1)


def count_messages_tokens(messages: list) -> int:
    """计算对话历史 + 当前消息的 token 总数（含固定开销）"""
    if not messages:
        return 0
    total = 0
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # 每条消息有固定开销（role 标记、分隔符等，OpenAI 格式约 4 tokens）
        total += count_tokens(content) + 4
    # 整体 prompt 有额外开销
    total += 2
    return total


# 导入智能体模块
from agents.router import AgentRouter, AgentType
from agents.academic_agent import AcademicAgent
from agents.student_services_agent import StudentServicesAgent
from agents.psychology_agent import PsychologyAgent
from agents.policy_agent import PolicyAgent
from agents.chat_agent import ChatAgent
from session_manager import session_manager
from env_utils import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

# 导入认证路由和依赖
from auth_routes import router as auth_router
from knowledge_base_routes import router as knowledge_base_router
from auth_utils import get_current_user
from database import init_db, User, AsyncSessionLocal, KnowledgeBaseModel, UsageLog
from rag_service import RAGService
from sqlalchemy import select
from jwxt_cli import JWXTClient

async def generate_session_topic(conversation_history: list) -> str:
    """
    根据对话历史生成会话主题
    
    使用 DeepSeek LLM 提取简洁的中文标题，失败时回退到最近用户消息截断
    """
    try:
        from langchain_deepseek import ChatDeepSeek
        from langchain_core.messages import SystemMessage, HumanMessage
        
        llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=20
        )
        
        # 取最近 4 条消息（2轮对话）作为上下文
        recent = conversation_history[-4:]
        history_text = "\n".join([
            f"{'用户' if m.get('role') == 'user' else '助手'}: {m.get('content', '')[:80]}"
            for m in recent
        ])
        
        messages = [
            SystemMessage(content="你是一个对话主题提取助手。请根据以下对话内容，生成一个不超过10个字的中文标题。直接返回标题文本，不要带引号、书名号或其他标点符号，不要有任何解释。"),
            HumanMessage(content=history_text)
        ]
        
        response = await llm.ainvoke(messages)
        topic = response.content.strip()
        # 去除常见标点
        for char in ['"', "'", "「", "」", "《", "》", "【", "】", ":", "："]:
            topic = topic.replace(char, "")
        topic = topic.replace("标题：", "").replace("主题：", "").strip()
        
        if len(topic) > 15:
            topic = topic[:15] + "..."
        if not topic:
            raise ValueError("生成的主题为空")
        return topic
    except Exception as e:
        print(f"[TopicGen] LLM 生成主题失败: {e}")
        # fallback: 取最近一条用户消息的前15字
        for m in reversed(conversation_history):
            if m.get("role") == "user":
                content = m.get("content", "").strip()
                return (content[:15] + "...") if len(content) > 15 else content
        return "新对话"


# 导入管理员路由
from admin_routes import router as admin_router

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
academic_agent = AcademicAgent()
student_services_agent = StudentServicesAgent()
psychology_agent = PsychologyAgent()
policy_agent = PolicyAgent()
chat_agent = ChatAgent()

# 智能体映射表
AGENTS = {
    AgentType.ACADEMIC: academic_agent,
    AgentType.STUDENT_SERVICES: student_services_agent,
    AgentType.PSYCHOLOGY: psychology_agent,
    AgentType.POLICY: policy_agent,
    AgentType.CHAT: chat_agent,
}


# ============ 流式输出辅助函数 ============

async def stream_response(
    message: str,
    session_id: str,
    agent_type: AgentType,
    conversation_history: list,
    user_info: Optional[dict] = None
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
    response_content = ""
    agent_type_str = "chat"
    action_taken = None

    try:
        agent = AGENTS.get(agent_type)

        if not agent:
            response_content = "您好！我是学生智能服务助手。我可以帮您处理：\n\n1. **学生学业**：选课、课表查询、成绩查询、GPA计算\n2. **学生办事**：证件补办、学费缴纳、饭卡充值、办事流程查询\n3. **心理咨询**：情绪疏导、压力调节、心理咨询预约\n4. **制度查询**：学籍管理、奖助学金、宿舍规定、考试纪律\n5. **日常聊天**：校园生活闲聊、一般性咨询\n\n请问有什么可以帮助您的？"
            agent_type_str = "chat"
            action_taken = None

            for i, char in enumerate(response_content):
                chunk = {
                    "type": "content",
                    "content": char,
                    "index": i,
                    "total": len(response_content)
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.005)

            end_chunk = {
                "type": "done",
                "agent_type": agent_type_str,
                "action_taken": action_taken,
                "session_id": session_id
            }
            yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
        else:
            async for result in agent.stream_process(
                message=message,
                session_id=session_id,
                context={"history": conversation_history, "user_info": user_info}
            ):
                if result["type"] == "content":
                    response_content += result["content"]
                    chunk = {
                        "type": "content",
                        "content": result["content"]
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0)
                elif result["type"] == "done":
                    agent_response = result["content"]
                    response_content = agent_response.content
                    agent_type_str = agent_response.agent_type
                    action_taken = agent_response.action_taken

                    end_chunk = {
                        "type": "done",
                        "agent_type": agent_type_str,
                        "action_taken": action_taken,
                        "session_id": session_id
                    }
                    yield f"data: {json.dumps(end_chunk, ensure_ascii=False)}\n\n"
                elif result["type"] == "error":
                    error_chunk = {
                        "type": "error",
                        "error": result["content"]
                    }
                    yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

        await session_manager.add_message(session_id, "user", message)
        await session_manager.add_message(session_id, "assistant", response_content, agent_type_str)
        
        # 记录调用用量统计（使用 tiktoken 精确计数）
        try:
            async with AsyncSessionLocal() as db:
                # 计算 prompt tokens：历史消息 + 当前消息 + 系统提示词固定开销
                system_overhead = 200  # 各 agent system prompt 的近似开销
                history_tokens = count_messages_tokens(conversation_history)
                prompt_tokens = count_tokens(message) + history_tokens + system_overhead
                completion_tokens = count_tokens(response_content)
                total_tokens = prompt_tokens + completion_tokens
                
                usage = UsageLog(
                    user_id=user_info.get("id") if user_info else None,
                    session_id=session_id,
                    agent_type=agent_type_str,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens
                )
                db.add(usage)
                await db.commit()
        except Exception as log_err:
            print(f"用量记录失败: {log_err}")
        
        # 周期性更新会话主题（每4条用户消息或第1条时更新）
        try:
            updated_history = await session_manager.get_conversation_history(session_id)
            user_msg_count = sum(1 for m in updated_history if m.get("role") == "user")
            if user_msg_count % 4 == 0 or user_msg_count == 1:
                new_topic = await generate_session_topic(updated_history)
                await session_manager.update_session_topic(session_id, new_topic)
                print(f"[TopicUpdate] 会话 {session_id[:8]}... 主题更新为: {new_topic}")
        except Exception as topic_err:
            print(f"[TopicUpdate] 更新会话主题失败: {topic_err}")

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


@app.post("/api/chat")
async def chat(request: ChatRequest, current_user: Optional[User] = Depends(get_current_user)):
    """
    主要对话端点（流式）
    
    接收用户消息，由系统自动路由到合适的智能体进行处理
    使用 Server-Sent Events (SSE) 实现流式输出
    """
    try:
        # 1. 准备用户信息
        user_info = None
        if current_user:
            user_info = {
                "id": current_user.id,
                "username": current_user.username,
                "full_name": current_user.full_name,
                "student_id": current_user.student_id,
                "email": current_user.email
            }
        
        # 2. 获取或创建会话
        session_id = request.session_id
        user_id = current_user.id if current_user else None
        if not session_id:
            session_id = await session_manager.create_session(user_id=user_id, user_info=user_info)
        else:
            session = await session_manager.get_session(session_id)
            if not session:
                # 会话不存在，创建新会话
                session_id = await session_manager.create_session(user_id=user_id, user_info=user_info)
        
        # 3. 获取对话历史
        conversation_history = await session_manager.get_conversation_history(session_id)
        
        # 4. 路由决策 - 选择智能体
        agent_type = await router.route(request.message, conversation_history)
        
        # 5. 返回流式响应
        return StreamingResponse(
            stream_response(
                message=request.message,
                session_id=session_id,
                agent_type=agent_type,
                conversation_history=conversation_history,
                user_info=user_info
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


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, current_user: Optional[User] = Depends(get_current_user)):
    """
    流式对话端点（推荐使用）
    
    使用Server-Sent Events (SSE)实现流式输出
    """
    try:
        # 1. 准备用户信息
        user_info = None
        if current_user:
            user_info = {
                "id": current_user.id,
                "username": current_user.username,
                "full_name": current_user.full_name,
                "student_id": current_user.student_id,
                "email": current_user.email
            }
        
        # 2. 获取或创建会话
        session_id = request.session_id
        user_id = current_user.id if current_user else None
        if not session_id:
            session_id = await session_manager.create_session(user_id=user_id, user_info=user_info)
        else:
            session = await session_manager.get_session(session_id)
            if not session:
                # 会话不存在，创建新会话
                session_id = await session_manager.create_session(user_id=user_id, user_info=user_info)
        
        # 3. 获取对话历史
        conversation_history = await session_manager.get_conversation_history(session_id)
        
        # 4. 路由决策 - 选择智能体
        agent_type = await router.route(request.message, conversation_history)
        
        # 4. 返回流式响应
        return StreamingResponse(
            stream_response(
                message=request.message,
                session_id=session_id,
                agent_type=agent_type,
                conversation_history=conversation_history,
                user_info=user_info
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
async def chat_direct(agent_type: str, request: ChatRequest, current_user: Optional[User] = Depends(get_current_user)):
    """
    直接指定智能体进行对话（非流式）
    
    Args:
        agent_type: 智能体类型 (academic / student_services / psychology / policy / chat)
    """
    try:
        # 获取或创建会话
        session_id = request.session_id
        user_id = current_user.id if current_user else None
        if not session_id:
            session_id = await session_manager.create_session(user_id=user_id)
        
        # 根据类型选择智能体
        if agent_type == "academic":
            agent = academic_agent
            agent_type_enum = AgentType.ACADEMIC
        elif agent_type == "student_services":
            agent = student_services_agent
            agent_type_enum = AgentType.STUDENT_SERVICES
        elif agent_type == "psychology":
            agent = psychology_agent
            agent_type_enum = AgentType.PSYCHOLOGY
        elif agent_type == "policy":
            agent = policy_agent
            agent_type_enum = AgentType.POLICY
        elif agent_type == "chat":
            agent = chat_agent
            agent_type_enum = AgentType.CHAT
        else:
            raise HTTPException(status_code=400, detail=f"未知的智能体类型: {agent_type}")
        
        # 获取对话历史
        conversation_history = await session_manager.get_conversation_history(session_id)
        
        # 调用智能体（统一使用 stream_process 并在内部收集结果）
        response_content = ""
        agent_response = None
        async for result in agent.stream_process(
            message=request.message,
            session_id=session_id,
            context={"history": conversation_history}
        ):
            if result["type"] == "content":
                response_content += result["content"]
            elif result["type"] == "done":
                agent_response = result["content"]
            elif result["type"] == "error":
                response_content = result["content"]
        
        # 优先使用 done 事件中封装的 AgentResponse，否则回退到收集的文本
        if agent_response:
            final_content = agent_response.content
            action_taken = agent_response.action_taken
        else:
            final_content = response_content
            action_taken = None
        
        # 保存对话历史
        await session_manager.add_message(session_id, "user", request.message)
        await session_manager.add_message(session_id, "assistant", final_content, agent_type)
        
        # 周期性更新会话主题
        try:
            updated_history = await session_manager.get_conversation_history(session_id)
            user_msg_count = sum(1 for m in updated_history if m.get("role") == "user")
            if user_msg_count % 4 == 0 or user_msg_count == 1:
                new_topic = await generate_session_topic(updated_history)
                await session_manager.update_session_topic(session_id, new_topic)
                print(f"[TopicUpdate] 会话 {session_id[:8]}... 主题更新为: {new_topic}")
        except Exception as topic_err:
            print(f"[TopicUpdate] 更新会话主题失败: {topic_err}")
        
        return ChatResponse(
            response=final_content,
            session_id=session_id,
            agent_type=agent_type,
            action_taken=action_taken
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


class CreateSessionRequest(BaseModel):
    """创建会话请求模型"""
    user_info: Optional[dict] = None


@app.post("/api/session")
async def create_session(request: CreateSessionRequest, current_user: Optional[User] = Depends(get_current_user)):
    """
    创建新会话
    """
    try:
        user_id = current_user.id if current_user else None
        session_id = await session_manager.create_session(user_id=user_id, user_info=request.user_info)
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@app.get("/api/sessions")
async def get_user_sessions(current_user: Optional[User] = Depends(get_current_user)):
    """
    获取用户的会话列表
    
    Returns:
        List[SessionInfo]: 会话列表
    """
    try:
        if not current_user:
            return []
        sessions = await session_manager.get_user_sessions(current_user.id)
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@app.get("/api/agents")
async def list_agents():
    """列出所有可用的智能体"""
    return {
        "agents": [
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
            },
            {
                "type": "student_services",
                "name": "学生办事智能体",
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
                "type": "psychology",
                "name": "心理咨询智能体",
                "description": "提供心理支持、情绪疏导、心理健康知识和心理咨询预约服务",
                "capabilities": [
                    "情绪疏导与倾听",
                    "心理压力调节建议",
                    "心理咨询预约信息",
                    "心理健康知识科普",
                    "紧急心理危机求助"
                ]
            },
            {
                "type": "policy",
                "name": "制度查询智能体",
                "description": "查询学校各类规章制度、政策文件、管理办法和相关办事部门信息",
                "capabilities": [
                    "学籍管理制度",
                    "奖助学金政策",
                    "宿舍管理规定",
                    "考试纪律",
                    "学位授予条件",
                    "违纪处分规定"
                ]
            },
            {
                "type": "chat",
                "name": "日常聊天智能体",
                "description": "处理校园生活闲聊、一般性咨询、问候和寒暄",
                "capabilities": [
                    "校园生活闲聊",
                    "一般性问题解答",
                    "问候和寒暄",
                    "校园设施位置咨询",
                    "生活小贴士"
                ]
            }
        ]
    }


# ============ 后台任务 ============

async def init_rag_index():
    """启动时检查并初始化 RAG 向量索引"""
    try:
        rag = RAGService()
        count = await rag.count_documents()
        if count == 0:
            print("向量库为空，正在从 MySQL 重建索引...")
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(KnowledgeBaseModel))
                items = result.scalars().all()
                if items:
                    docs = [
                        {
                            "id": item.id,
                            "title": item.title,
                            "content": item.content,
                            "category": item.category,
                            "agent_type": item.agent_type
                        }
                        for item in items
                    ]
                    await rag.rebuild(docs)
                    print(f"RAG 索引重建完成，共 {len(docs)} 条文档")
                else:
                    print("MySQL 知识库为空，无需重建 RAG 索引")
        else:
            print(f"RAG 向量库已有 {count} 个文档片段")
    except Exception as e:
        print(f"RAG 索引初始化失败: {e}")


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

    # 注册知识库路由
    app.include_router(knowledge_base_router)

    # 注册管理员路由
    app.include_router(admin_router)

    # 初始化 RAG 索引
    await init_rag_index()

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
    print("  - POST /api/chat           智能路由对话（非流式）")
    print("  - POST /api/chat/stream    智能路由对话（流式）")
    print("  - POST /api/chat/direct    指定智能体对话")
    print("  - GET  /api/agents         查看可用智能体")
    print("  - GET  /api/knowledge-base 获取知识库列表")
    print("  - POST /api/knowledge-base 添加知识库项")
    print("  - POST /api/knowledge-base/search 语义搜索")
    print("  - DELETE /api/knowledge-base/{id} 删除知识库项")
    print("  - GET  /docs               API 文档")
    print("=" * 50)
    print("智能体列表:")
    print("  - academic          学生学业智能体")
    print("  - student_services  学生办事智能体")
    print("  - psychology        心理咨询智能体")
    print("  - policy            制度查询智能体")
    print("  - chat              日常聊天智能体")
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
