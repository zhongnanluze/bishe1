"""
学生学业智能体
处理：选课、课表查询、成绩查询、学业规划
"""

from typing import Dict, Optional, List, AsyncGenerator
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from .base_agent import BaseAgent
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from env_utils import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from rag_service import RAGService

# 导入教务系统客户端
try:
    from jwxt_cli import JWXTClient
    JWXT_AVAILABLE = True
except ImportError:
    JWXT_AVAILABLE = False
    print("警告：无法导入jwxt_cli模块，成绩和课表查询将使用模拟数据")

# 全局教务系统客户端实例（单例）
_jwxt_client = None


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

def get_jwxt_client():
    """获取或创建教务系统客户端单例"""
    global _jwxt_client
    if _jwxt_client is None and JWXT_AVAILABLE:
        _jwxt_client = JWXTClient.from_browser()
    return _jwxt_client

@tool
def query_course_schedule(student_id: str, xn: str = None, xq: int = None) -> str:
    """
    查询学生课表

    Args:
        student_id: 学号
        xn: 学年（可选，如：2024-2025）
        xq: 学期（可选，1或2）
    """
    if JWXT_AVAILABLE:
        client = get_jwxt_client()
        if client:
            try:
                schedule = client.get_schedule(xn=xn, xq=xq)
                if schedule:
                    return f"【{student_id} 的课表】\n\n" + str(schedule)
                return f"无法获取{student_id}的课表，请检查是否已登录教务系统"
            except Exception as e:
                return f"查询课表失败：{str(e)}"

    # 如果无法使用真实系统，回退到模拟数据
    if student_id not in STUDENT_COURSES_DB:
        return f"未找到学号 {student_id} 的选课记录。"

    course_codes = STUDENT_COURSES_DB[student_id]
    courses_info = []

    for code in course_codes:
        if code in COURSES_DB:
            course = COURSES_DB[code]
            courses_info.append(f"📚 {course['name']} ({code})\n   ⏰ {course['time']}\n   📍 {course['location']}\n   👨‍🏫 {course['teacher']}\n   📝 {course['credits']}学分")

    return f"【{student_id} 的课表】\n\n" + "\n\n".join(courses_info) + "\n\n⚠️ 以上为模拟示例数据，请以教务系统实际查询结果为准。"


@tool
def query_grades(student_id: str, semester: str = None, xn: str = None, xq: int = None) -> str:
    """
    查询学生成绩

    Args:
        student_id: 学号
        semester: 学期（可选，如：2024-2025-1）
        xn: 学年（可选，如：2024-2025）
        xq: 学期（可选，1或2）
    """
    if JWXT_AVAILABLE:
        client = get_jwxt_client()
        if client:
            try:
                grades = client.get_grades(xn=xn, xq=xq)
                if grades:
                    client.print_grades(grades)

                    result = f"## {student_id} 的成绩单\n\n"
                    result += "| 学期 | 课程名称 | 成绩 |\n"
                    result += "|------|---------|------|\n"

                    filtered_count = 0
                    for row in grades:
                        if len(row) >= 7:
                            try:
                                term = row[1]
                                course_name = row[3]
                                score = row[5]

                                if semester and semester not in str(term):
                                    continue
                                if xn and xn not in str(term):
                                    continue
                                if xq is not None and str(xq) not in str(term):
                                    continue

                                result += f"| {term} | {course_name} | {score} |\n"
                                filtered_count += 1
                            except:
                                pass

                    if filtered_count == 0 and (semester or xn or xq is not None):
                        return f"未找到 {student_id} 在指定学期的成绩记录（学期：{semester or xn + '-' + str(xq)}）。请确认学期信息是否正确。"

                    return result
                return f"无法获取{student_id}的成绩，请检查是否已登录教务系统"
            except Exception as e:
                return f"查询成绩失败：{str(e)}"

    # 如果无法使用真实系统，回退到模拟数据
    if student_id not in GRADES_DB:
        return f"未找到学号 {student_id} 的成绩记录。"

    grades = GRADES_DB[student_id]

    if semester:
        grades = {k: v for k, v in grades.items() if v["semester"] == semester}

    if not grades:
        return f"未找到该学期的成绩记录。"

    result = f"## {student_id} 的成绩单\n\n"
    result += "| 课程名称 | 成绩 | GPA |\n"
    result += "|---------|------|-----|\n"

    total_gpa = 0
    total_credits = 0
    for code, info in grades.items():
        course_name = COURSES_DB.get(code, {}).get("name", code)
        credits = COURSES_DB.get(code, {}).get("credits", 0)
        result += f"| {course_name} | {info['grade']}分 | {info['gpa']} |\n"
        total_gpa += info['gpa'] * credits
        total_credits += credits

    avg_gpa = total_gpa / total_credits if total_credits > 0 else 0

    result += f"\n### 统计信息\n"
    result += f"- 平均GPA：{avg_gpa:.2f}\n"
    result += f"- 总学分：{total_credits}\n"

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

    return f"【{student_id} 学业统计】\n\n总学分：{total_credits}\n平均GPA：{gpa:.2f}\n\nGPA等级：\n- 4.0：优秀 (90-100分)\n- 3.7：良好 (85-89分)\n- 3.3：中等 (82-84分)\n- 3.0：及格 (78-81分)\n- 2.7：及格 (75-77分)\n\n⚠️ 以上为模拟示例数据，请以教务系统实际查询结果为准。"


class AcademicAgent(BaseAgent):
    """学生学业智能体"""

    def __init__(self):
        llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=2048
        )

        tools = [
            query_course_schedule,
            query_grades,
            search_courses,
            select_course,
            drop_course,
            get_academic_calendar,
            calculate_gpa
        ]

        system_prompt = """你是文泽奇妙小AI的学业助手，专业、高效的学习伙伴。

你的职责：
- 课表查询：查看学生的课程安排
- 成绩查询：查询各科成绩和GPA
- 选课服务：帮助学生查询和选择课程
- 学业规划：提供学业日历和重要时间节点
- 学业政策咨询：回答学分、绩点、考试、毕业要求等相关政策问题

工作准则：
- 使用提供的工具函数完成任务
- 获取工具结果后，用亲切自然的语言向学生解释和说明
- 成绩、课表、课程列表等涉及具体数据的内容，必须完整保留并呈现所有原始信息（包括每一门课的名称、成绩、学分、时间、地点等），不要省略任何一条记录
- 如已提供学号，直接使用该学号进行查询
- 回复中适当使用表情符号，让语气更友好
- 当用户询问学业政策、规章制度等信息时，请优先参考知识库内容作答
- 不要编造你不确定的信息，优先使用知识库提供的内容

特别注意：
- 当用户提到"大一"、"大二"、"大三"、"大四"时，需要将其转换为具体的学期参数：
  - 大一：2024-2025-1 和 2024-2025-2
  - 大二：2025-2026-1 和 2025-2026-2
  - 大三：2026-2027-1 和 2026-2027-2
  - 大四：2027-2028-1 和 2027-2028-2
- 当用户查询特定年级的成绩时，必须调用 query_grades 工具并传递相应的学期参数
- 例如，查询"大二的成绩"时，应该分别查询 2025-2026-1 和 2025-2026-2 两个学期的成绩

当前用户信息：
- 姓名：{full_name}
- 学号：{student_id}
"""

        super().__init__(
            name="学生学业智能体",
            description="处理学生学业相关需求，包括选课、课表查询、成绩查询、学业规划等",
            llm=llm,
            tools=tools,
            system_prompt=system_prompt,
            agent_type="academic"
        )
        self.rag_service = RAGService()

    async def _build_knowledge_context(self, query: str) -> str:
        """检索知识库并格式化上下文"""
        results = await self.rag_service.search(query, top_k=3, agent_type="academic")
        if not results:
            return ""
        context = "\n\n【知识库参考信息】\n"
        for r in results:
            snippet = r['content'][:400] + ('...' if len(r['content']) > 400 else '')
            context += f"· [{r['title']}] {snippet}\n"
        return context

    async def stream_process(self, message: str, session_id: str, context: Dict = None) -> AsyncGenerator[Dict, None]:
        """流式处理学业相关请求"""
        user_info = context.get("user_info", {}) if context else {}
        student_id = user_info.get("student_id")
        full_name = user_info.get("full_name") or user_info.get("username")

        # 将用户信息填充到系统提示词中
        filled_system_prompt = self.base_system_prompt.format(
            full_name=full_name or "未知",
            student_id=student_id or "未知"
        )

        knowledge_context = await self._build_knowledge_context(message)
        async for chunk in self._run_stream(
            message, session_id, context, knowledge_context, system_prompt=filled_system_prompt
        ):
            yield chunk
