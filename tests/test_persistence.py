"""
OJ System - Step 6: 数据持久化、备份与恢复测试
"""
import os
import json
import time
import pytest


@pytest.fixture
def _setup_data(admin_client, teacher_client, student_client):
    """创建用户、题目、提交，产生完整数据"""
    # 创建题目
    teacher_client.post("/api/problems", json={
        "id": "P3001",
        "title": "Persistence Test",
        "description": "desc",
        "input_description": "input",
        "output_description": "output",
        "samples": [{"input": "1\n", "output": "1\n"}],
        "time_limit": 2.0,
        "memory_limit": 128,
        "difficulty": "easy",
        "tags": [],
        "test_cases": [
            {"case_id": "c1", "input": "1\n", "output": "1\n", "score": 100, "is_hidden": False},
        ],
    })
    # 学生提交代码
    student_client.post("/api/submissions", json={
        "problem_id": "P3001",
        "language": "python",
        "source_code": "print(int(input()))",
    })
    time.sleep(1.5)  # 等待评测完成


class TestBackupCreation:
    """备份创建测试"""

    def test_create_backup(self, admin_client, _setup_data):
        """创建备份 → 201"""
        resp = admin_client.post("/api/admin/backups")
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["backup_id"].startswith("backup_")
        assert "created_at" in data

    def test_list_backups(self, admin_client, _setup_data):
        """查询备份列表"""
        admin_client.post("/api/admin/backups")
        resp = admin_client.get("/api/admin/backups")
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) >= 1

    def test_student_cannot_create_backup(self, student_client, _setup_data):
        """学生无权创建备份 → 403"""
        resp = student_client.post("/api/admin/backups")
        assert resp.status_code == 403

    def test_teacher_cannot_create_backup(self, teacher_client, _setup_data):
        """教师无权创建备份 → 403"""
        resp = teacher_client.post("/api/admin/backups")
        assert resp.status_code == 403


class TestBackupRestore:
    """备份恢复测试"""

    def test_restore_success(self, admin_client, _setup_data):
        """创建备份 → 修改数据 → 恢复 → 数据还原"""
        # 创建备份
        resp = admin_client.post("/api/admin/backups")
        backup_id = resp.json()["data"]["backup_id"]

        # 记录当前题目数量
        orig_problems = admin_client.get("/api/problems").json()["data"]["items"]
        orig_count = len(orig_problems)

        # 删除题目（模拟数据变更）
        admin_client.delete("/api/problems/P3001")
        # 等待删除生效
        after_delete = admin_client.get("/api/problems").json()["data"]["items"]
        assert len(after_delete) < orig_count

        # 恢复备份
        resp2 = admin_client.post(f"/api/admin/backups/{backup_id}/restore")
        assert resp2.status_code == 200

        # 验证数据恢复
        after_restore = admin_client.get("/api/problems").json()["data"]["items"]
        assert len(after_restore) == orig_count

    def test_restore_nonexistent_backup(self, admin_client):
        """恢复不存在的备份 → 404"""
        resp = admin_client.post("/api/admin/backups/nonexistent_id/restore")
        assert resp.status_code == 404

    def test_restore_by_student(self, student_client, _setup_data):
        """学生无权恢复 → 403"""
        resp = student_client.post("/api/admin/backups/some_id/restore")
        assert resp.status_code == 403

    def test_backup_contains_required_files(self, admin_client, _setup_data):
        """验证备份包含所需文件"""
        resp = admin_client.post("/api/admin/backups")
        backup_id = resp.json()["data"]["backup_id"]

        # 检查磁盘上的备份文件
        from app.repositories.manager import BACKUP_DIR
        backup_path = os.path.join(BACKUP_DIR, backup_id)
        assert os.path.isdir(backup_path)
        assert os.path.exists(os.path.join(backup_path, "manifest.json"))
        assert os.path.exists(os.path.join(backup_path, "users.json"))
        assert os.path.exists(os.path.join(backup_path, "problems.json"))


class TestPersistence:
    """数据持久化测试（JSON 文件）"""

    def test_data_survives_restart(self, admin_client, _setup_data):
        """验证数据已写入磁盘文件"""
        from app.repositories.manager import DATA_DIR

        # 检查数据文件存在且非空
        users_path = os.path.join(DATA_DIR, "users.json")
        problems_path = os.path.join(DATA_DIR, "problems.json")
        submissions_path = os.path.join(DATA_DIR, "submissions.json")

        for path in [users_path, problems_path, submissions_path]:
            assert os.path.exists(path), f"{path} should exist"
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, dict), f"{path} should be a dict"

        # 验证题目确实持久化了
        with open(problems_path, "r", encoding="utf-8") as f:
            problems = json.load(f)
        assert "P3001" in problems

    def test_corrupted_backup_does_not_destroy_data(self, admin_client, _setup_data):
        """损坏的备份恢复失败且不破坏现有数据"""
        # 手动创建一个损坏的备份目录
        from app.repositories.manager import BACKUP_DIR, DATA_DIR
        import shutil

        bad_backup_dir = os.path.join(BACKUP_DIR, "backup_corrupt")
        os.makedirs(bad_backup_dir, exist_ok=True)
        # 写入一个无效的 manifest
        with open(os.path.join(bad_backup_dir, "manifest.json"), "w") as f:
            f.write("not valid json {{{")

        # 记录恢复前的数据
        with open(os.path.join(DATA_DIR, "problems.json"), "r") as f:
            before = f.read()

        # 尝试恢复
        resp = admin_client.post("/api/admin/backups/backup_corrupt/restore")
        assert resp.status_code in (400, 500)  # 应该失败

        # 验证数据未被破坏
        with open(os.path.join(DATA_DIR, "problems.json"), "r") as f:
            after = f.read()
        assert before == after

        # 清理
        shutil.rmtree(bad_backup_dir, ignore_errors=True)
