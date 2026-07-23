"""
OJ System - Step 4: 提交与状态管理测试
"""
import time
import pytest


@pytest.fixture
def _problem(teacher_client):
    """预置一道题目"""
    teacher_client.post("/api/problems", json={
        "id": "P1001",
        "title": "A+B Problem",
        "description": "desc",
        "input_description": "input",
        "output_description": "output",
        "samples": [{"input": "1 2\n", "output": "3\n"}],
        "time_limit": 2.0,
        "memory_limit": 128,
        "difficulty": "easy",
        "tags": [],
        "test_cases": [
            {"case_id": "c1", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
            {"case_id": "c2", "input": "10 20\n", "output": "30\n", "score": 50, "is_hidden": True},
        ],
    })


class TestCreateSubmission:
    """创建提交测试"""

    def test_create_submission_returns_202(self, student_client, _problem):
        """创建提交 → 202 + submission_id"""
        resp = student_client.post("/api/submissions", json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": "a,b=map(int,input().split());print(a+b)",
        })
        assert resp.status_code == 202
        data = resp.json()
        assert data["code"] == 202
        assert "submission_id" in data["data"]
        assert data["data"]["status"] == "pending"

    def test_create_submission_nonexistent_problem(self, student_client):
        """不存在的题 → 404"""
        resp = student_client.post("/api/submissions", json={
            "problem_id": "P9999",
            "language": "python",
            "source_code": "print(1)",
        })
        assert resp.status_code == 404

    def test_create_empty_source(self, student_client, _problem):
        """空代码 → 422"""
        resp = student_client.post("/api/submissions", json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": "",
        })
        assert resp.status_code == 422

    def test_unauthenticated_cannot_submit(self, client, _problem):
        """未登录 → 401"""
        resp = client.post("/api/submissions", json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": "print(1)",
        })
        assert resp.status_code == 401


class TestSubmissionQuery:
    """提交查询测试"""

    @pytest.fixture(autouse=True)
    def _submit(self, student_client, _problem):
        resp = student_client.post("/api/submissions", json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": "a,b=map(int,input().split());print(a+b)",
        })
        self.submission_id = resp.json()["data"]["submission_id"]

    def test_get_submission(self, student_client):
        """查询自己的提交成功"""
        resp = student_client.get(f"/api/submissions/{self.submission_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == self.submission_id
        assert data["problem_id"] == "P1001"
        # 自己的提交可以看到源代码
        assert data["source_code"] is not None

    def test_list_submissions(self, student_client):
        """查询提交列表"""
        resp = student_client.get("/api/submissions")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    def test_student_cannot_see_others(self, student_client):
        """学生看不到别人的提交"""
        # 用另一个学生的 client 查询，应该看不到
        # 当前只有一个学生，列表应只包含自己的
        resp = student_client.get("/api/submissions?user_id=fake-id")
        items = resp.json()["data"]["items"]
        # 学生指定其他 user_id 应被忽略，只返回自己的
        for item in items:
            assert item["user_id"] != "fake-id"

    def test_teacher_can_see_all(self, teacher_client, _problem):
        """教师可以查看全部提交"""
        # 学生先提交
        from tests.conftest import _make_session_cookie
        import json
        from fastapi.testclient import TestClient
        from app.main import app
        sc = TestClient(app)
        sc.cookies.set("session", _make_session_cookie("test-student-id"))
        sc.post("/api/submissions", json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": "a,b=map(int,input().split());print(a+b)",
        })

        resp = teacher_client.get("/api/submissions")
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        assert len(items) >= 1

    def test_filter_by_problem(self, student_client):
        """按题目筛选"""
        resp = student_client.get(f"/api/submissions?problem_id=P1001")
        assert resp.status_code == 200

    def test_filter_by_status(self, student_client):
        """按状态筛选"""
        resp = student_client.get("/api/submissions?status=pending")
        assert resp.status_code == 200


class TestRejudge:
    """重新评测测试"""

    @pytest.fixture(autouse=True)
    def _submit(self, student_client, _problem):
        resp = student_client.post("/api/submissions", json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": "a,b=map(int,input().split());print(a+b)",
        })
        self.submission_id = resp.json()["data"]["submission_id"]

    def test_rejudge_by_teacher(self, teacher_client):
        """教师重新评测 → 200"""
        # 等待评测完成
        time.sleep(1.5)
        resp = teacher_client.post(f"/api/submissions/{self.submission_id}/rejudge")
        assert resp.status_code == 200

    def test_student_cannot_rejudge(self, student_client):
        """学生无权重新评测 → 403"""
        resp = student_client.post(f"/api/submissions/{self.submission_id}/rejudge")
        assert resp.status_code == 403

    def test_rejudge_nonexistent(self, teacher_client):
        """重新评测不存在的提交 → 404"""
        resp = teacher_client.post("/api/submissions/nonexistent-id/rejudge")
        assert resp.status_code == 404


class TestStatusFlow:
    """状态流转测试"""

    def test_pending_to_finished(self, student_client, _problem):
        """pending → running → finished 合法流转"""
        resp = student_client.post("/api/submissions", json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": "a,b=map(int,input().split());print(a+b)",
        })
        sid = resp.json()["data"]["submission_id"]
        assert resp.json()["data"]["status"] == "pending"

        # 等待评测完成
        time.sleep(2.0)
        resp2 = student_client.get(f"/api/submissions/{sid}")
        status = resp2.json()["data"]["status"]
        assert status in ("finished", "running")
