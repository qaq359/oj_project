"""
OJ System - Data Repository Manager
初始化数据目录和文件，提供统一的数据访问接口。
"""
import os
import json
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

_lock = threading.Lock()


def ensure_directories():
    """确保所有必要的目录存在"""
    for d in [DATA_DIR, TEMP_DIR, BACKUP_DIR]:
        os.makedirs(d, exist_ok=True)


def load_json(filename: str) -> dict:
    """从 data 目录加载 JSON 文件"""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_json(filename: str, data: dict) -> None:
    """原子写入 JSON 文件到 data 目录"""
    filepath = os.path.join(DATA_DIR, filename)
    tmp_path = filepath + ".tmp"
    with _lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp_path, filepath)


def init_data():
    """初始化数据目录和默认数据文件"""
    ensure_directories()

    # 初始化各个数据文件（如果不存在）
    data_files = {
        "users.json": {},
        "problems.json": {},
        "submissions.json": {},
        "judge_logs.json": {},
        "audit_logs.json": {},
        "backups.json": {},
    }

    for filename, default in data_files.items():
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            save_json(filename, default)

    # 创建默认管理员账号
    _ensure_default_admin()


def _ensure_default_admin():
    """首次启动时创建默认管理员账号"""
    import bcrypt

    users = load_json("users.json")
    admin_id = None
    for uid, u in users.items():
        if u.get("role") == "admin":
            admin_id = uid
            break

    if admin_id is not None:
        return  # 管理员已存在

    admin_id = "00000000-0000-0000-0000-000000000001"
    hashed = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    users[admin_id] = {
        "id": admin_id,
        "username": "admin",
        "password_hash": hashed,
        "role": "admin",
        "is_active": True,
        "created_at": "2026-07-16T00:00:00Z",
        "updated_at": "2026-07-16T00:00:00Z",
    }
    save_json("users.json", users)
