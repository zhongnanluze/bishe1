"""
智能体系统模块
包含：路由器、学生学业智能体、学生办事智能体、心理咨询智能体、制度查询智能体、日常聊天智能体
"""

from .router import AgentRouter
from .academic_agent import AcademicAgent
from .student_services_agent import StudentServicesAgent
from .psychology_agent import PsychologyAgent
from .policy_agent import PolicyAgent
from .chat_agent import ChatAgent

__all__ = [
    'AgentRouter',
    'AcademicAgent',
    'StudentServicesAgent',
    'PsychologyAgent',
    'PolicyAgent',
    'ChatAgent'
]
