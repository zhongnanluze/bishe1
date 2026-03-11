"""
学生学业智能体
处理：选课、课表查询、成绩查询、学业规划
"""

from typing import Dict, Optional, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from .base_agent import BaseAgent, AgentResponse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env_utils import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL


# ============ 模拟数据库 ============

# 模拟课程数据
COURSES_DB = {
    "CS101": {"name": "计算机导论", "credits": 3, "teacher": "张教授", "time": "周一 8:00-9:40", "location": "教学楼A101", "capacity": 120, "enrolled": 98},
    "CS201": {"name": "数据结构与算法", "credits": 4, "teacher": "李教授", "time": "周二 14:00-15:40", "location": "教学楼B203", "capacity": 80, "enrolled": 76},
    "CS301": {"name": "操作系统", "credits": 4, "teacher": "王教授", "time": "周三 10:00-11:40", "location": "实验楼C305", "capacity": 60, "enrolled": 55},
    "CS302": {"name": "计算机网络", "credits": 3, "teacher": "赵教授", "time": "周四 14:00-15:40", "location": "教学楼A205", "capacity": 70, "enrolled": 68},
    "MATH101": {"name": "高等数学", "credits": 5, "teacher": "刘教授", "time": "周一 14:00-16:30", "location": "教学楼A301", "capacity": 150, "enrolled": 145},
    "ENG101": {"name": "大学英语", "credits": 3, "teacher": "Smith", "time": "周五 8:00-9:40", "location": "外语楼E102", "capacity": 40, "enrolled": 38},
}

# 模拟学生选课数据
STUDENT_COURSES_DB = {
    "2024001": ["CS101", "MATH101", "ENG101"],
    "2024002": ["CS201", "CS301", "MATH101"],
}

# 模拟成绩数据
GRADES_DB = {
    "2024001": {
        "CS101": {"grade": 85, "gpa": 3.5, "semester": "2024-2025-1"},
        "MATH101": {"grade": 92, "gpa": 4.0, "semester": "2024-2025-1"},
        "ENG101": {"grade": 78, "gpa": 3.0, "semester": "2024-2025-1"},
    },
    "2024002": {
        "CS201": {"grade": 88, "gpa": 3.7, "semester": "2024-2025-1"},
        "CS301": {"grade": 90, "gpa": 4.0, "semester": "2024-2025-1"},
        "MATH101": {"grade": 85, "gpa": 3.5, "semester": "2024-2025-1"},
    }
}


# ============ 工具函数定义 ============

@tool
def query_course_schedule(student_id: str) -> str:
    """
    查询学生课表
    
    Args:
        student_id: 学号
    """
    if student_id not in STUDENT_COURSES_DB:
        return f"未找到学号 {student_id} 的选课记录。"
    
    course_codes = STUDENT_COURSES_DB[student_id]
    courses_info = []
    
    for code in course_codes:
        if code in COURSES_DB:
            course = COURSES_DB[code]
            courses_info.append(f"📚 {course['name']} ({code})\n   ⏰ {course['time']}\n   📍 {course['location']}\n   👨‍🏫 {course['teacher']}\n   📝 {course['credits']}学分")
    
    return f"【{student_id} 的课表】\n\n" + "\n\n".join(courses_info)


@tool
def query_grades(student_id: str, semester: str = None) -> str:
    """
    查询学生成绩
    
    Args:
        student_id: 学号
        semester: 学期（可选，如：2024-2025-1）
    """
    if student_id not in GRADES_DB:
        return f"未找到学号 {student_id} 的成绩记录。"
    
    grades = GRADES_DB[student_id]
    
    if semester:
        grades = {k: v for k, v in grades.items() if v["semester"] == semester}
    
    if not grades:
        return f"未找到该学期的成绩记录。"
    
    grades_info = []
    total_gpa = 0
    total_credits = 0
    
    for code, info in grades.items():
        course_name = COURSES_DB.get(code, {}).get("name", code)
        credits = COURSES_DB.get(code, {}).get("credits", 0)
        grades_info.append(f"📖 {course_name}\n   成绩：{info['grade']}分  GPA：{info['gpa']}")
        total_gpa += info['gpa'] * credits
        total_credits += credits
    
    avg_gpa = total_gpa / total_credits if total_credits > 0 else 0
    
    result = f"【{student_id} 的成绩单】\n\n"
    result += "\n\n".join(grades_info)
    result += f"\n\n📊 平均GPA：{avg_gpa:.2f}"
    
    return result


@tool
def search_courses(keyword: str = None, course_type: str = None) -> str:
    """
    搜索可选课程
    
    Args:
        keyword: 关键词（课程名或课程代码）
        course_type: 课程类型（可选：专业课/通识课/选修课）
    """
    results = []
    
    for code, course in COURSES_DB.items():
        if keyword and keyword.upper() not in code and keyword not in course["name"]:
            continue
        
        remaining = course["capacity"] - course["enrolled"]
        status = "🟢 可选" if remaining > 0 else "🔴 已满"
        
        results.append(
            f"📚 {course['name']} ({code})\n"
            f"   ⏰ {course['time']} | 📍 {course['location']}\n"
            f"   👨‍🏫 {course['teacher']} | 📝 {course['credits']}学分\n"
            f"   👥 剩余名额：{remaining}/{course['capacity']} {status}"
        )
    
    if not results:
        return "未找到符合条件的课程。"
    
    return "【可选课程列表】\n\n" + "\n\n".join(results)


@tool
def select_course(student_id: str, course_code: str) -> str:
    """
    学生选课
    
    Args:
        student_id: 学号
        course_code: 课程代码
    """
    if course_code not in COURSES_DB:
        return f"课程代码 {course_code} 不存在。"
    
    course = COURSES_DB[course_code]
    remaining = course["capacity"] - course["enrolled"]
    
    if remaining <= 0:
        return f"【选课失败】\n课程 {course['name']} 已满员，请选择其他课程。"
    
    # 模拟选课成功
    if student_id not in STUDENT_COURSES_DB:
        STUDENT_COURSES_DB[student_id] = []
    
    if course_code in STUDENT_COURSES_DB[student_id]:
        return f"【提示】\n您已经选了课程 {course['name']}，无需重复选择。"
    
    COURSES_DB[course_code]["enrolled"] += 1
    STUDENT_COURSES_DB[student_id].append(course_code)
    
    return f"【选课成功】✅\n\n课程：{course['name']} ({course_code})\n时间：{course['time']}\n地点：{course['location']}\n学分：{course['credits']}\n\n请按时上课！"


@tool
def drop_course(student_id: str, course_code: str) -> str:
    """
    学生退课
    
    Args:
        student_id: 学号
        course_code: 课程代码
    """
    if student_id not in STUDENT_COURSES_DB:
        return f"未找到学号 {student_id} 的选课记录。"
    
    if course_code not in STUDENT_COURSES_DB[student_id]:
        return f"您未选择课程 {course_code}。"
    
    course = COURSES_DB.get(course_code, {})
    course_name = course.get("name", course_code)
    
    # 模拟退课
    STUDENT_COURSES_DB[student_id].remove(course_code)
    if course_code in COURSES_DB:
        COURSES_DB[course_code]["enrolled"] -= 1
    
    return f"【退课成功】✅\n\n已退选课程：{course_name} ({course_code})\n\n注意：退课后该课程的学分将不计入本学期。"


@tool
def get_academic_calendar() -> str:
    """获取学业日历/重要时间节点"""
    return """
【2024-2025学年学业日历】

📅 第一学期：
- 开学：2024年9月1日
- 选课时间：9月1日-9月7日
- 补考：开学后第2周
- 期中考试：第10周
- 期末考试：第18-19周
- 寒假：2025年1月15日开始

📅 第二学期：
- 开学：2025年2月20日
- 期中考试：第10周
- 期末考试：第18-19周
- 暑假：2025年7月5日开始

⚠️ 重要提醒：
- 选课退改选截止时间：开学第2周周五
- 成绩复核申请：成绩公布后1周内
- 补考报名：开学前1周
    """


@tool
def calculate_gpa(student_id: str) -> str:
    """
    计算学生GPA
    
    Args:
        student_id: 学号
    """
    if student_id not in GRADES_DB:
        return f"未找到学号 {student_id} 的成绩记录。"
    
    grades = GRADES_DB[student_id]
    total_gpa_points = 0
    total_credits = 0
    
    for code, info in grades.items():
        credits = COURSES_DB.get(code, {}).get("credits", 0)
        total_gpa_points += info['gpa'] * credits
        total_credits += credits
    
    gpa = total_gpa_points / total_credits if total_credits > 0 else 0
    
    return f"【{student_id} 学业统计】\n\n总学分：{total_credits}\n平均GPA：{gpa:.2f}\n\nGPA等级：\n- 4.0：优秀 (90-100分)\n- 3.7：良好 (85-89分)\n- 3.3：中等 (82-84分)\n- 3.0：及格 (78-81分)\n- 2.7：及格 (75-77分)"


class AcademicAgent(BaseAgent):
    """学生学业智能体"""
    
    def __init__(self):
        super().__init__(
            name="学生学业智能体",
            description="处理学生学业相关需求，包括选课、课表查询、成绩查询、学业规划等"
        )
        self.llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=2048
        )
        # 绑定工具
        self.tools = [
            query_course_schedule,
            query_grades,
            search_courses,
            select_course,
            drop_course,
            get_academic_calendar,
            calculate_gpa
        ]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
    
    async def process(self, message: str, session_id: str, context: Dict = None) -> AgentResponse:
        """处理学业相关请求"""
        
        # 系统提示词
        system_prompt = """你是学生学业智能助手，专门帮助学生处理各类学业事务。

你的职责：
1. 选课服务：帮助学生查询可选课程、完成选课/退课操作
2. 课表查询：查看学生的课程安排
3. 成绩查询：查询各科成绩和GPA
4. 学业规划：提供学业日历、重要时间节点提醒

注意事项：
- 处理学业事务前需要确认学生身份（学号）
- 选课时提醒学生注意课程时间冲突
- 提供学业建议时考虑学生的实际情况
- 对于复杂问题，分步骤指导学生操作

请使用提供的工具函数来帮助学生完成学业事务。"""
        
        # 构建消息列表
        messages = [SystemMessage(content=system_prompt)]
        
        # 添加历史对话
        for hist in self.conversation_history:
            if hist["role"] == "user":
                messages.append(HumanMessage(content=hist["content"]))
            else:
                messages.append(AIMessage(content=hist["content"]))
        
        # 添加当前消息
        messages.append(HumanMessage(content=message))
        
        try:
            # 调用LLM
            response = self.llm_with_tools.invoke(messages)
            
            # 处理工具调用
            if response.tool_calls:
                # 执行工具调用
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    
                    # 找到对应的工具并执行
                    for tool_func in self.tools:
                        if tool_func.name == tool_name:
                            result = tool_func.invoke(tool_call)
                            tool_results.append(result)
                            break
                
                # 构建最终响应
                final_content = "\n\n".join(tool_results)
                action_taken = f"执行了 {len(tool_results)} 个工具操作"
            else:
                final_content = response.content
                action_taken = None
            
            # 更新历史
            self.add_to_history("user", message)
            self.add_to_history("assistant", final_content)
            
            return AgentResponse(
                content=final_content,
                agent_type="academic",
                action_taken=action_taken
            )
            
        except Exception as e:
            return AgentResponse(
                content=f"抱歉，处理您的请求时出现错误：{str(e)}。请稍后重试或联系教务处。",
                agent_type="academic",
                action_taken="error"
            )
