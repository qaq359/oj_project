"""
OJ System - 认证业务逻辑
"""
import uuid
from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException, Request

from app.repositories.manager import load_json, save_json


def _now_iso() -> str:
    """返回当前 UTC 时间的 ISO 8601 格式字符串"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_user(user: dict) -> dict:
    """移除敏感字段（password_hash），返回安全的用户信息"""
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user.get("role", "student"),
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at", ""),
        "updated_at": user.get("updated_at", ""),
    }


def register(username: str, password: str) -> dict:
    """
    注册新用户。
    注册用户默认角色为 student。
    username 重复 → 409
    """
    users = load_json("users.json")

    # 检查用户名唯一性
    for u in users.values():
        if u.get("username") == username:
            raise HTTPException(status_code=409, detail="username already exists")

    user_id = str(uuid.uuid4())
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = _now_iso()

    user = {
        "id": user_id,
        "username": username,
        "password_hash": password_hash,
        "role": "student",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    users[user_id] = user
    save_json("users.json", users)

    return _sanitize_user(user)


def login(request: Request, username: str, password: str) -> dict:
    """
    用户登录。
    失败统一返回 401（不区分用户名错还是密码错）。
    is_active=false → 403
    """
    users = load_json("users.json")

    # 查找用户
    matched = None
    for u in users.values():
        if u.get("username") == username:
            matched = u
            break

    if matched is None:
        raise HTTPException(status_code=401, detail="invalid username or password")

    # 检查密码
    if not bcrypt.checkpw(password.encode("utf-8"), matched["password_hash"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="invalid username or password")

    # 检查是否被禁用
    if not matched.get("is_active", False):
        raise HTTPException(status_code=403, detail="user is disabled")

    # 写入 Session
    request.session["user_id"] = matched["id"]

    return _sanitize_user(matched)


def logout(request: Request) -> None:
    """登出：清除 Session"""
    request.session.clear()


def get_me(request: Request) -> dict:
    """获取当前登录用户信息（从 Session 中）"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    users = load_json("users.json")
    user = users.get(user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="User not found")

    return _sanitize_user(user)
