"""
OJ System - 用户管理业务逻辑
"""
from datetime import datetime, timezone

from fastapi import HTTPException

from app.repositories.manager import load_json, save_json
from app.models.enums import UserRole


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 格式字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_user(user: dict) -> dict:
    """移除敏感字段"""
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user.get("role", "student"),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at", ""),
        "updated_at": user.get("updated_at", ""),
    }


def list_users(page: int = 1, page_size: int = 20) -> dict:
    """获取分页用户列表"""
    users_data = load_json("users.json")
    all_users = [_sanitize_user(u) for u in users_data.values()]

    total = len(all_users)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": all_users[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_user(user_id: str) -> dict:
    """获取单个用户信息"""
    users = load_json("users.json")
    if user_id not in users:
        raise HTTPException(status_code=404, detail="user not found")
    return _sanitize_user(users[user_id])


def update_user(operator_id: str, target_id: str, role: str | None, is_active: bool | None) -> dict:
    """
    修改用户角色或启用状态。
    仅 admin 可操作。
    不允许管理员禁用自己。
    role 只能是 student/teacher/admin。
    """
    users = load_json("users.json")

    if target_id not in users:
        raise HTTPException(status_code=404, detail="user not found")

    # 不允许管理员修改自己的任何属性
    if operator_id == target_id:
        raise HTTPException(status_code=400, detail="cannot modify your own account")

    user = users[target_id]
    now = _now_iso()

    if role is not None:
        if role not in (UserRole.STUDENT.value, UserRole.TEACHER.value, UserRole.ADMIN.value):
            raise HTTPException(status_code=422, detail="invalid role")
        user["role"] = role
        user["updated_at"] = now

    if is_active is not None:
        user["is_active"] = is_active
        user["updated_at"] = now

    users[target_id] = user
    save_json("users.json", users)

    return _sanitize_user(user)
