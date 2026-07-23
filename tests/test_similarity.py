"""
OJ System - Adv 3: 代码相似度检测测试
"""
import pytest
from app.services.similarity_service import (
    preprocess_code,
    ast_fingerprint,
    calculate_similarity,
    run_similarity_check,
)


class TestPreprocess:
    """代码预处理测试"""

    def test_remove_blank_lines(self):
        code = "a = 1\n\nb = 2\n\n\n"
        result = preprocess_code(code)
        assert "\n\n" not in result
        assert result.count("\n") == 1

    def test_remove_comments(self):
        code = "# this is a comment\na = 1  # inline comment\nb = 2"
        result = preprocess_code(code)
        assert "#" not in result
        assert "a = 1" in result
        assert "b = 2" in result

    def test_keep_string_hashes(self):
        code = 's = "#not a comment"\nx = 1'
        result = preprocess_code(code)
        assert "#not a comment" in result


class TestASTFingerprint:
    """AST 归一化测试"""

    def test_identical_code_same_fingerprint(self):
        fp1 = ast_fingerprint("a = 1\nb = 2\nprint(a + b)")
        fp2 = ast_fingerprint("a = 1\nb = 2\nprint(a + b)")
        assert fp1 == fp2

    def test_renamed_variables_same_structure(self):
        """不同变量名但相同结构 → 指纹相同"""
        fp1 = ast_fingerprint("x = 1\ny = 2\nprint(x + y)")
        fp2 = ast_fingerprint("foo = 1\nbar = 2\nprint(foo + bar)")
        assert fp1 == fp2  # 归一化后应该相同

    def test_different_structure_different_fingerprint(self):
        """不同结构 → 指纹不同"""
        fp1 = ast_fingerprint("a = 1\nb = 2\nprint(a + b)")
        fp2 = ast_fingerprint("a = 1\nprint(a)\nb = 2")
        assert fp1 != fp2

    def test_syntax_error_returns_none(self):
        fp = ast_fingerprint("this is not valid python {{{")
        assert fp is None

    def test_empty_code_returns_none(self):
        fp = ast_fingerprint("")
        assert fp is None


class TestSimilarity:
    """相似度计算测试"""

    def test_identical_is_1(self):
        fp = ast_fingerprint("a = 1\nprint(a)")
        assert calculate_similarity(fp, fp) == 1.0

    def test_different_structure_low(self):
        fp1 = ast_fingerprint("a = 1\nprint(a)")
        fp2 = ast_fingerprint("for i in range(10):\n    print(i)")
        sim = calculate_similarity(fp1, fp2)
        assert sim < 0.8  # 不同结构应低于阈值

    def test_highly_similar_above_threshold(self):
        """高度相似代码 → 高于阈值"""
        code1 = "x = int(input())\nif x > 0:\n    print('positive')\nelse:\n    print('negative')"
        code2 = "n = int(input())\nif n > 0:\n    print('positive')\nelse:\n    print('negative')"
        fp1 = ast_fingerprint(code1)
        fp2 = ast_fingerprint(code2)
        sim = calculate_similarity(fp1, fp2)
        assert sim >= 0.7  # 达到系统阈值


class TestIntegration:
    """集成测试：通过 API 检测"""

    def test_similarity_check_api(self, teacher_client):
        """教师调用相似度检测 API"""
        # 先创建题目和两份提交
        teacher_client.post("/api/problems", json={
            "id": "P9999",
            "title": "Similarity Test",
            "description": "desc", "input_description": "in", "output_description": "out",
            "samples": [{"input": "1\n", "output": "1\n"}],
            "time_limit": 2.0, "memory_limit": 128, "difficulty": "easy", "tags": [],
            "test_cases": [{"case_id": "c1", "input": "1\n", "output": "1\n",
                            "score": 100, "is_hidden": False}],
        })

        # 模拟两份提交（需要手动插入 data）
        import json, os, uuid
        from app.repositories.manager import DATA_DIR, save_json, load_json

        sid1 = str(uuid.uuid4())
        sid2 = str(uuid.uuid4())
        now = "2026-07-22T00:00:00Z"

        subs = load_json("submissions.json")
        subs[sid1] = {"id": sid1, "user_id": "u1", "problem_id": "P9999",
                       "language": "python",
                       "source_code": "x=int(input())\nprint(x*2)",
                       "status": "finished", "result": "AC", "score": 100,
                       "total_time": 0.1, "created_at": now, "started_at": now, "finished_at": now}
        subs[sid2] = {"id": sid2, "user_id": "u2", "problem_id": "P9999",
                       "language": "python",
                       "source_code": "n=int(input())\nprint(n*2)",
                       "status": "finished", "result": "AC", "score": 100,
                       "total_time": 0.1, "created_at": now, "started_at": now, "finished_at": now}
        save_json("submissions.json", subs)

        # 调用检测
        resp = teacher_client.post("/api/problems/P9999/similarity-check")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_pairs"] >= 1

    def test_student_cannot_check(self, student_client):
        """学生无权检测 → 403"""
        resp = student_client.post("/api/problems/P1001/similarity-check")
        assert resp.status_code == 403

    def test_similarity_reports_api(self, teacher_client):
        """查询相似度报告"""
        resp = teacher_client.get("/api/problems/P1001/similarity-reports")
        assert resp.status_code == 200
