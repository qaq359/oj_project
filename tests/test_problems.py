"""
OJ System - Step 1: 题目管理测试
"""
import pytest


class TestProblemCreation:
    """题目创建相关测试"""

    def test_create_problem_success(self, teacher_client, sample_problem):
        """创建合法题目 → 201"""
        resp = teacher_client.post("/api/problems", json=sample_problem)
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == 201
        assert data["data"]["id"] == "P1001"
        assert data["data"]["title"] == "A+B Problem"

    def test_create_duplicate_id(self, teacher_client, sample_problem):
        """重复创建同编号 → 409"""
        teacher_client.post("/api/problems", json=sample_problem)
        resp = teacher_client.post("/api/problems", json=sample_problem)
        assert resp.status_code == 409

    def test_create_missing_required_fields(self, teacher_client):
        """缺少必填字段 → 422"""
        resp = teacher_client.post("/api/problems", json={"id": "P0001"})
        assert resp.status_code == 422

    def test_create_invalid_score_sum(self, teacher_client, sample_problem):
        """测试点分值总和不为 100 → 422"""
        sample_problem["test_cases"][0]["score"] = 30
        resp = teacher_client.post("/api/problems", json=sample_problem)
        assert resp.status_code == 422

    def test_create_empty_test_cases(self, teacher_client, sample_problem):
        """测试点为空 → 422"""
        sample_problem["test_cases"] = []
        resp = teacher_client.post("/api/problems", json=sample_problem)
        assert resp.status_code == 422

    def test_create_invalid_id_format(self, teacher_client, sample_problem):
        """题号含非法字符 → 422"""
        sample_problem["id"] = "P@#$"
        resp = teacher_client.post("/api/problems", json=sample_problem)
        assert resp.status_code == 422

    def test_student_cannot_create(self, student_client, sample_problem):
        """学生无权创建 → 403"""
        resp = student_client.post("/api/problems", json=sample_problem)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create(self, client, sample_problem):
        """未登录创建 → 401"""
        resp = client.post("/api/problems", json=sample_problem)
        assert resp.status_code == 401


class TestProblemQuery:
    """题目查询相关测试"""

    @pytest.fixture(autouse=True)
    def _setup_problem(self, teacher_client, sample_problem):
        teacher_client.post("/api/problems", json=sample_problem)

    def test_list_problems(self, student_client):
        """查询题目列表成功"""
        resp = student_client.get("/api/problems")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert len(data["data"]["items"]) == 1
        item = data["data"]["items"][0]
        assert item["id"] == "P1001"
        assert item["title"] == "A+B Problem"
        assert "test_cases" not in item

    def test_get_problem_detail_student(self, student_client):
        """学生查看题目详情：无 test_cases"""
        resp = student_client.get("/api/problems/P1001")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["test_cases"] is None
        assert data["samples"] is not None

    def test_get_problem_detail_teacher(self, teacher_client):
        """教师查看题目详情：包含 test_cases"""
        resp = teacher_client.get("/api/problems/P1001")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["test_cases"] is not None
        assert len(data["test_cases"]) == 2

    def test_student_cannot_see_hidden_testcase(self, student_client):
        """学生看不到隐藏测试点"""
        resp = student_client.get("/api/problems/P1001")
        assert resp.status_code == 200
        # 学生响应中 test_cases 应为 None
        assert resp.json()["data"]["test_cases"] is None

    def test_get_nonexistent_problem(self, student_client):
        """查询不存在的题目 → 404"""
        resp = student_client.get("/api/problems/P9999")
        assert resp.status_code == 404

    def test_unauthenticated_list(self, client):
        """未登录查询列表 → 401"""
        resp = client.get("/api/problems")
        assert resp.status_code == 401


class TestProblemUpdate:
    """题目修改相关测试"""

    @pytest.fixture(autouse=True)
    def _setup_problem(self, teacher_client, sample_problem):
        teacher_client.post("/api/problems", json=sample_problem)

    def test_update_problem_title(self, teacher_client):
        """修改题目标题 → 200"""
        resp = teacher_client.put("/api/problems/P1001", json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "New Title"

    def test_update_nonexistent_problem(self, teacher_client):
        """修改不存在的题目 → 404"""
        resp = teacher_client.put("/api/problems/P9999", json={"title": "X"})
        assert resp.status_code == 404

    def test_cannot_change_problem_id(self, teacher_client):
        """不允许通过修改接口改题号（id 字段应被忽略）"""
        resp = teacher_client.put("/api/problems/P1001", json={"id": "P9999", "title": "Changed"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        # id 不应改变
        assert data["id"] == "P1001"

    def test_update_invalid_score_sum(self, teacher_client):
        """修改测试点分值不为 100 → 422"""
        resp = teacher_client.put("/api/problems/P1001", json={
            "test_cases": [
                {"case_id": "c1", "input": "1\n", "output": "1\n", "score": 30, "is_hidden": False},
            ]
        })
        assert resp.status_code == 422

    def test_student_cannot_update(self, student_client):
        """学生无权修改 → 403"""
        resp = student_client.put("/api/problems/P1001", json={"title": "Hacked"})
        assert resp.status_code == 403


class TestProblemDelete:
    """题目删除相关测试"""

    @pytest.fixture(autouse=True)
    def _setup_problem(self, teacher_client, sample_problem):
        teacher_client.post("/api/problems", json=sample_problem)

    def test_delete_problem(self, teacher_client):
        """删除题目 → 200"""
        resp = teacher_client.delete("/api/problems/P1001")
        assert resp.status_code == 200

        # 删除后查询 → 404
        resp2 = teacher_client.get("/api/problems/P1001")
        assert resp2.status_code == 404

    def test_delete_nonexistent_problem(self, teacher_client):
        """删除不存在的题目 → 404"""
        resp = teacher_client.delete("/api/problems/P9999")
        assert resp.status_code == 404

    def test_student_cannot_delete(self, student_client):
        """学生无权删除 → 403"""
        resp = student_client.delete("/api/problems/P1001")
        assert resp.status_code == 403

    def test_unauthenticated_cannot_delete(self, client):
        """未登录删除 → 401"""
        resp = client.delete("/api/problems/P1001")
        assert resp.status_code == 401
