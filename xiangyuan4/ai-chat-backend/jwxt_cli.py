#!/usr/bin/env python3
"""
沈阳工业大学教务系统 CLI 工具
基于正方教务系统（JWXT）标准接口
使用方法：
1. 首先在浏览器中登录教务系统
2. 允许 Chrome 远程调试（chrome://inspect/#remote-debugging）
3. 运行此脚本
功能：
- 查询成绩
- 查询课表
- 查询考试安排
- 查询个人信息
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
import time
from datetime import datetime
import re

# 自动安装依赖
import importlib.util
for pkg in ['websockets']:
    if importlib.util.find_spec(pkg) is None:
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

# 添加 skill scripts 路径
skill_dir = r"D:\qlcaw\QClaw\resources\openclaw\config\skills\browser-cdp\scripts"
if os.path.exists(skill_dir):
    sys.path.insert(0, skill_dir)

BASE_URL = "https://jwxt.sut.edu.cn"


class JWXTClient:
    """正方教务系统客户端"""

    def __init__(self, cookie=None, cdp_client=None, main_tab_id=None):
        self.cookie = cookie
        self.cdp_client = cdp_client
        self.main_tab_id = main_tab_id
        self.session_id = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://jwxt.sut.edu.cn/jsxsd/framework/xsMain.jsp',
        }
        if cookie:
            self.headers['Cookie'] = cookie

    @classmethod
    def from_browser(cls):
        """从浏览器获取 cookie"""
        try:
            from browser_launcher import BrowserLauncher
            from cdp_client import CDPClient
        except ImportError:
            print("无法导入 browser_launcher 模块")
            return None

        print("连接浏览器获取 Cookie...")
        launcher = BrowserLauncher()
        try:
            cdp_url = launcher.launch(browser='chrome', reuse_profile=True, wait_for_user=True)
        except Exception as e:
            print(f"连接失败: {e}")
            return None

        client = CDPClient(cdp_url)
        client.connect()

        # 找到教务系统标签页
        tabs = client.list_tabs()
        target_tab = None
        for t in tabs:
            if 'jwxt.sut.edu.cn' in t['url']:
                target_tab = t
                break

        if not target_tab:
            print("未找到教务系统标签页，请先登录教务系统")
            return None

        # attach 到目标标签页
        client.attach(target_tab['id'])

        # 启用 Network 域并获取 cookie
        try:
            client.send('Network.enable')
        except:
            pass

        result = client.send('Network.getAllCookies')
        cookies = result.get('cookies', [])

        # 过滤教务系统相关的 cookie
        jwxt_cookies = [c for c in cookies if 'jwxt' in c.get('domain', '') or 'sut.edu.cn' in c.get('domain', '')]
        if not jwxt_cookies:
            jwxt_cookies = cookies

        cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in jwxt_cookies])
        print(f"已获取 Cookie ({len(jwxt_cookies)} 个)")

        return cls(cookie=cookie_str, cdp_client=client, main_tab_id=target_tab['id'])

    def request(self, path, data=None, method='GET'):
        """发送请求"""
        url = f"{BASE_URL}{path}"
        req = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except urllib.error.HTTPError as e:
            print(f"HTTP 错误: {e.code} {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"URL 错误: {e.reason}")
            return None

    def get_grades(self, xn=None, xq=None):
        """查询成绩"""
        path = "/jsxsd/kscj/cjcx_list"
        print(f"\n查询成绩...")
        if xn:
            print(f"   学年: {xn}")
        if xq:
            print(f"   学期: {xq}")
        html = self.request(path)
        if not html:
            return None
        return self._parse_grades(html)

    def _parse_grades(self, html):
        """解析成绩 HTML"""
        grades = []
        row_pattern = r'<tr[^>]*>.*?</tr>'
        rows = re.findall(row_pattern, html, re.DOTALL)
        for row in rows:
            cell_pattern = r'<td[^>]*>(.*?)</td>'
            cells = re.findall(cell_pattern, row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            cells = [re.sub(r'&nbsp;', '', c) for c in cells]
            if len(cells) >= 5:
                try:
                    if cells[0].isdigit():
                        grades.append(cells)
                except:
                    pass
        return grades

    def print_grades(self, grades):
        """格式化打印成绩"""
        if not grades:
            print("无成绩记录")
            return
        print("\n" + "=" * 100)
        print(f"{'序号':<4} {'学年学期':<12} {'课程名称':<25} {'成绩':<6} {'学分':<5} {'课程性质':<10}")
        print("=" * 100)
        shown_courses = {}
        for row in grades:
            if len(row) < 7:
                continue
            try:
                idx = row[0]
                term = row[1]
                course_name = row[3]
                score = row[5]
                credit = row[7] if len(row) > 7 else ''
                course_type = row[12] if len(row) > 12 else ''
                if score.isdigit():
                    score_val = int(score)
                elif score in ['合格', '不合格', '优秀', '良好', '中等', '及格', '不及格']:
                    score_val = 60 if score in ['合格', '及格', '中等', '良好', '优秀'] else 0
                else:
                    score_val = 0
                key = (term, course_name)
                if key not in shown_courses or score_val > shown_courses[key][4]:
                    shown_courses[key] = (idx, term, course_name, score, credit, course_type, score_val)
            except:
                continue
        for key in sorted(shown_courses.keys()):
            idx, term, course_name, score, credit, course_type, _ = shown_courses[key]
            if len(course_name) > 22:
                course_name = course_name[:22] + '...'
            print(f"{idx:<4} {term:<12} {course_name:<25} {score:<6} {credit:<5} {course_type:<10}")
        print("=" * 100)
        print(f"共 {len(shown_courses)} 门课程")
        total_credits = 0
        passed = 0
        for row in shown_courses.values():
            try:
                total_credits += float(row[4]) if row[4] else 0
                if row[6] >= 60:
                    passed += 1
            except:
                pass
        print(f"总学分: {total_credits}, 通过率: {passed}/{len(shown_courses)}")

    def get_schedule(self, xn=None, xq=None, zc=None):
        """查询课表 - 使用 CDP 从 iframe 获取"""
        print(f"\n查询课表...")
        if not self.cdp_client:
            print("无 CDP 连接，请先调用 from_browser() 创建客户端")
            return None

        client = self.cdp_client
        if self.main_tab_id:
            client.attach(self.main_tab_id)
        else:
            tabs = client.list_tabs()
            main_tab = None
            for t in tabs:
                if 'xsMain.jsp' in t['url']:
                    main_tab = t
                    break
            if not main_tab:
                print("未找到教务系统主页面")
                return None
            client.attach(main_tab['id'])

        js_get_schedule = '''
        (function() {
            var iframe = document.getElementById('Frame1');
            if (!iframe) {
                var iframes = document.querySelectorAll('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    if (iframes[i].src && iframes[i].src.indexOf('xskb') >= 0) {
                        iframe = iframes[i];
                        break;
                    }
                }
            }
            if (!iframe) return {error: 'iframe not found'};
            try {
                var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                var tables = iframeDoc.querySelectorAll('table');
                var scheduleData = [];
                for (var t = 0; t < tables.length; t++) {
                    var rows = tables[t].querySelectorAll('tr');
                    for (var r = 0; r < rows.length; r++) {
                        var cells = rows[r].querySelectorAll('td');
                        var rowData = [];
                        for (var c = 0; c < cells.length; c++) {
                            rowData.push(cells[c].innerText.trim());
                        }
                        if (rowData.length > 0 && rowData.some(function(x) { return x.length > 0; })) {
                            scheduleData.push(rowData);
                        }
                    }
                }
                return {scheduleData: scheduleData};
            } catch(e) {
                return {error: e.message};
            }
        })()
        '''

        result = client.send('Runtime.evaluate', {
            'expression': js_get_schedule,
            'returnByValue': True
        })
        data = result.get('result', {}).get('value', {})
        if 'error' in data:
            print(f"获取失败: {data['error']}")
            return None
        return data.get('scheduleData', [])

    def parse_schedule(self, html):
        """解析课表 HTML"""
        schedule = {}
        row_pattern = r'<tr[^>]*>.*?</tr>'
        rows = re.findall(row_pattern, html, re.DOTALL)
        current_period = 0
        for row in rows:
            cell_pattern = r'<td[^>]*>(.*?)</td>'
            cells = re.findall(cell_pattern, row, re.DOTALL)
            if not cells:
                continue
            if '星期' in cells[0] or '节次' in ''.join(cells):
                continue
            current_period += 1
            for day_idx, cell in enumerate(cells):
                if day_idx == 0:
                    continue
                cell_text = re.sub(r'<br\s*/?>', ' ', cell)
                cell_text = re.sub(r'<[^>]+>', '', cell_text)
                cell_text = re.sub(r'&nbsp;', '', cell_text)
                cell_text = cell_text.strip()
                if cell_text and len(cell_text) > 1:
                    day = day_idx
                    if day not in schedule:
                        schedule[day] = {}
                    schedule[day][current_period] = cell_text
        return schedule

    def print_schedule(self, schedule):
        """格式化打印课表"""
        if not schedule:
            print("无课表数据")
            return
        print("\n" + "=" * 100)
        print("课程表")
        print("=" * 100)
        for i, row in enumerate(schedule[:20]):
            if i == 0:
                print(' | '.join(row[:8]))
                print("-" * 100)
            else:
                display = [c[:15] for c in row[:8]]
                print(' | '.join(display))
        if len(schedule) > 20:
            print(f"... 还有 {len(schedule) - 20} 行")
        print("=" * 100)
        print(f"共 {len(schedule)} 门课程")

    def get_exams(self):
        """查询考试安排"""
        path = "/jsxsd/ksap/ksap_list"
        print(f"\n查询考试安排...")
        html = self.request(path)
        if not html:
            return None
        return html

    def get_info(self):
        """查询个人信息"""
        path = "/jsxsd/grxx/grxxcx"
        print(f"\n查询个人信息...")
        html = self.request(path)
        if not html:
            return None
        return html

    def test_connection(self):
        """测试连接是否有效"""
        path = "/jsxsd/framework/xsMain.jsp"
        html = self.request(path)
        if html and ('学籍成绩' in html or '教学一体化' in html):
            print("连接有效")
            return True
        else:
            print("连接无效，请重新登录")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='沈阳工业大学教务系统 CLI 工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('command', choices=['grades', 'schedule', 'exams', 'info', 'test'],
                        help='操作命令: grades(成绩), schedule(课表), exams(考试), info(个人信息), test(测试)')
    parser.add_argument('--cookie', '-c', help='指定 Cookie')
    parser.add_argument('--xn', help='学年，如 2024-2025')
    parser.add_argument('--xq', type=int, choices=[1, 2], help='学期 1 或 2')
    parser.add_argument('--zc', type=int, help='周次')
    parser.add_argument('--output', '-o', help='输出文件')
    parser.add_argument('--json', action='store_true', help='JSON 格式输出')
    args = parser.parse_args()

    print("=" * 60)
    print("沈阳工业大学教务系统 CLI")
    print("=" * 60)

    if args.cookie:
        client = JWXTClient(cookie=args.cookie)
    else:
        client = JWXTClient.from_browser()
        if not client:
            print("\n提示：请先在浏览器中登录教务系统并允许远程调试")
            print("   或使用 --cookie 参数手动提供 Cookie")
            sys.exit(1)

    result = None
    if args.command == 'test':
        client.test_connection()
    elif args.command == 'grades':
        result = client.get_grades(xn=args.xn, xq=args.xq)
        if result:
            client.print_grades(result)
    elif args.command == 'schedule':
        result = client.get_schedule(xn=args.xn, xq=args.xq, zc=args.zc)
        if result:
            client.print_schedule(result)
    elif args.command == 'exams':
        result = client.get_exams()
    elif args.command == 'info':
        result = client.get_info()

    if result and args.output:
        if args.json:
            output = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            output = str(result)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\n已保存到: {args.output}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
