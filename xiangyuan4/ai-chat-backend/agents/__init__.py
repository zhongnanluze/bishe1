"""
智能体系统模块
包含：路由器、学生事务智能体、学生学业智能体
"""

from .router import AgentRouter
from .student_affairs_agent import StudentAffairsAgent
from .academic_agent import AcademicAgent

__all__ = ['AgentRouter', 'StudentAffairsAgent', 'AcademicAgent']
