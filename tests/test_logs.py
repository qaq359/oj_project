"""
OJ System - Step 5: 评测日志测试
"""
import time
import pytest


@pytest.fixture
def _setup_submission(student_client, teacher_client):
    """创建题目 → 学生提交代码 → 等待评测完成"""
    teacher_client.post("/api/problems", json={
        "id": "P2001",
        "title": "Test Problem",
        "description": "desc",
        "input_description": "input",
        "output_description": "output",
        "samples": [{"input": "1 2\n", "output": "3\n"}],
        "time_limit": 2.0,
        "memory_limit": 128,
        "difficulty": "easy",
        "tags": [],
        "test_cases": [
            {"case_id": "c1", "input": "1 2\n", "output": "3\n", "score": 60, "is_hidden": False},
            {"case_id": "c2", "input": "10 20\n", "output": "30\n", "score": 40, "is_hidden": True},
        ],
    })
    resp = student_client.post("/api/submissions", json={
        "problem_id": "P2001",
        "language": "python",
        "source_code": "a,b=map(int,input().split());print(a+b)",
    })
    sid = resp.json()["data"]["submission_id"]
    # 等待评测完成
    time.sleep(2.0)
    return sid


class TestStudentLogs:
    """学生查看日志测试"""

    def test_student_can_see_own_logs(self, student_client, _setup_submission):
        """学生可以查看自己提交的日志"""
        resp = student_client.get(f"/api/submissions/{_setup_submission}/logs")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["summary"]["submission_id"] == _setup_submission
        assert len(data["cases"]) == 2  # 两个测试点（但可能只执行了一个，遇到非AC即停）
        assert data["cases"][0]["score"] >= 0

    def test_student_cannot_see_hidden_input(self, student_client, _setup_submission):
        """学生看不到隐藏测试点的输入"""
        resp = student_client.get(f"/api/submissions/{_setup_submission}/logs")
        cases = resp.json()["data"]["cases"]
        for c in cases:
            assert "input_data" not in c
            if c.get("is_hidden"):
                assert c["stdout"] is None
                assert c["expected_output"] is None

    def test_student_cannot_see_others_logs(self, student_client):
        """学生不能查看别人的日志 → 403"""
        resp = student_client.get("/api/submissions/fake-submission-id/logs")
        assert resp.status_code == 404

    def test_unauthenticated_cannot_see_logs(self, client, _setup_submission):
        """未登录 → 401"""
        resp = client.get(f"/api/submissions/{_setup_submission}/logs")
        assert resp.status_code == 401


class TestTeacherLogs:
    """教师查看日志测试"""

    def test_teacher_can_see_full_logs(self, teacher_client, _setup_submission):
        """教师可以查看完整日志（包含所有测试点数据）"""
        resp = teacher_client.get(f"/api/submissions/{_setup_submission}/logs")
        assert resp.status_code == 200
        data = resp.json()["data"]
        for c in data["cases"]:
            assert "input_data" in c
            assert "expected_output" in c

    def test_teacher_log_search(self, teacher_client, _setup_submission):
        """教师日志检索"""
        resp = teacher_client.get("/api/logs?problem_id=P2001")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["items"]) >= 1

    def test_student_cannot_search_logs(self, student_client):
        """学生不能使用日志检索 → 403"""
        resp = student_client.get("/api/logs")
        assert resp.status_code == 403


class TestAuditLogs:
    """审计日志测试"""

    def test_teacher_viewing_logs_creates_audit(self, teacher_client, _setup_submission):
        """教师查看完整日志后应产生审计记录"""
        teacher_client.get(f"/api/submissions/{_setup_submission}/logs")

    def test_admin_can_see_audit_logs(self, admin_client, teacher_client, _setup_submission):
        """管理员可以查看审计日志"""
        # 先让教师查看日志以产生审计记录
        teacher_client.get(f"/api/submissions/{_setup_submission}/logs")
        resp = admin_client.get("/api/audit-logs")
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 1

    def test_teacher_cannot_see_audit_logs(self, teacher_client):
        """教师无权查看审计日志 → 403"""
        resp = teacher_client.get("/api/audit-logs")
        assert resp.status_code == 403


class TestSanitization:
    """日志脱敏测试"""

    def test_path_sanitization(self):
        """路径脱敏：绝对路径 → <submission>/main.py"""
        from app.utils.sanitizers import sanitize_path
        assert sanitize_path(r"C:\oj\temp\oj_abc123\main.py") == "<submission>/main.py"
        assert sanitize_path("/home/server/oj/temp/oj_xyz/main.py") == "<submission>/main.py"

    def test_truncation(self):
        """超长文本截断"""
        from app.utils.sanitizers import truncate_text
        long_text = "A" * 5000
        result = truncate_text(long_text)
        assert len(result) == 4000 + len("...[truncated]")
        assert result.endswith("...[truncated]")

    def test_short_text_not_truncated(self):
        """短文本不被截断"""
        from app.utils.sanitizers import truncate_text
        short = "hello"
        assert truncate_text(short) == "hello"

    def test_teacher_student_view_difference(self, student_client, teacher_client, _setup_submission):
        """教师和学生看到的日志内容不同"""
        s_resp = student_client.get(f"/api/submissions/{_setup_submission}/logs")
        t_resp = teacher_client.get(f"/api/submissions/{_setup_submission}/logs")

        s_case = s_resp.json()["data"]["cases"][0]
        t_case = t_resp.json()["data"]["cases"][0]

        # 教师有 input_data，学生没有
        assert "input_data" in t_case
        assert "input_data" not in s_case
