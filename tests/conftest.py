"""
OJ System - pytest 公共夹具
"""
import os
import json
import pytest
from fastapi.testclient import TestClient

# 确保使用测试数据目录
os.environ.setdefault("OJ_TESTING", "1")

from app.main import app
from app.repositories.manager import DATA_DIR, ensure_directories, save_json, load_json

TEST_DATA_DIR = os.path.join(os.path.dirname(DATA_DIR), "test_data")


def _init_test_data():
    """初始化测试数据目录"""
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    for f in ["users.json", "problems.json", "submissions.json",
              "judge_logs.json", "audit_logs.json", "backups.json"]:
        path = os.path.join(TEST_DATA_DIR, f)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as fp:
                json.dump({}, fp)


def _seed_test_users():
    """预置测试用户：student、teacher、admin"""
    import bcrypt
    users = {
        "test-student-id": {
            "id": "test-student-id",
            "username": "test_student",
            "password_hash": bcrypt.hashpw("student123".encode(), bcrypt.gensalt()).decode(),
            "role": "student",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
        "test-teacher-id": {
            "id": "test-teacher-id",
            "username": "test_teacher",
            "password_hash": bcrypt.hashpw("teacher123".encode(), bcrypt.gensalt()).decode(),
            "role": "teacher",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
        "test-admin-id": {
            "id": "test-admin-id",
            "username": "test_admin",
            "password_hash": bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
            "role": "admin",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
    }
    with open(os.path.join(TEST_DATA_DIR, "users.json"), "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _make_session_cookie(user_id: str) -> str:
    """使用 Starlette SessionMiddleware 相同的密钥签名 session cookie"""
    import itsdangerous
    from base64 import b64encode

    secret = "oj-dev-secret-key-change-in-production"
    signer = itsdangerous.TimestampSigner(str(secret))

    # Session 数据：{"user_id": "..."}
    session_data = json.dumps({"user_id": user_id}).encode("utf-8")
    session_data_b64 = b64encode(session_data)
    signed = signer.sign(session_data_b64)
    return signed.decode("utf-8")


# ---- Fixtures ----


@pytest.fixture(autouse=True)
def setup_test_data(monkeypatch):
    """每个测试前：初始化测试数据，并将 DATA_DIR 重定向到测试目录"""
    _init_test_data()
    _seed_test_users()

    # 清空 problems 数据
    with open(os.path.join(TEST_DATA_DIR, "problems.json"), "w", encoding="utf-8") as f:
        json.dump({}, f)
    with open(os.path.join(TEST_DATA_DIR, "submissions.json"), "w", encoding="utf-8") as f:
        json.dump({}, f)
    with open(os.path.join(TEST_DATA_DIR, "judge_logs.json"), "w", encoding="utf-8") as f:
        json.dump({}, f)
    with open(os.path.join(TEST_DATA_DIR, "audit_logs.json"), "w", encoding="utf-8") as f:
        json.dump({}, f)

    # Monkeypatch repository manager 的数据目录
    import app.repositories.manager as mgr
    monkeypatch.setattr(mgr, "DATA_DIR", TEST_DATA_DIR)
    monkeypatch.setattr(mgr, "BACKUP_DIR", os.path.join(TEST_DATA_DIR, "backups"))
    os.makedirs(os.path.join(TEST_DATA_DIR, "backups"), exist_ok=True)


@pytest.fixture
def client():
    """未认证的测试客户端"""
    return TestClient(app)


@pytest.fixture
def student_client():
    """以学生身份认证的测试客户端"""
    c = TestClient(app)
    cookie = _make_session_cookie("test-student-id")
    c.cookies.set("session", cookie)
    return c


@pytest.fixture
def teacher_client():
    """以教师身份认证的测试客户端"""
    c = TestClient(app)
    cookie = _make_session_cookie("test-teacher-id")
    c.cookies.set("session", cookie)
    return c


@pytest.fixture
def admin_client():
    """以管理员身份认证的测试客户端"""
    c = TestClient(app)
    cookie = _make_session_cookie("test-admin-id")
    c.cookies.set("session", cookie)
    return c


@pytest.fixture
def sample_problem():
    """标准题目数据"""
    return {
        "id": "P1001",
        "title": "A+B Problem",
        "description": "输入两个整数 a 和 b，输出它们的和。",
        "input_description": "一行包含两个整数 a 和 b。",
        "output_description": "输出一个整数，表示 a+b。",
        "samples": [{"input": "1 2\n", "output": "3\n"}],
        "constraints": "|a|, |b| <= 10^9",
        "time_limit": 1.0,
        "memory_limit": 128,
        "difficulty": "easy",
        "tags": ["基础", "输入输出"],
        "test_cases": [
            {"case_id": "case_01", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
            {"case_id": "case_02", "input": "-1 2\n", "output": "1\n", "score": 50, "is_hidden": True},
        ],
    }
