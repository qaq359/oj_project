"""
OJ System - 权限依赖注入
所有受保护的路由通过此模块进行 Session 认证和角色校验。
"""
from fastapi import Request, HTTPException

from app.repositories.manager import load_json


async def get_current_user(request: Request) -> dict:
    """
    从 Session 中获取当前登录用户。
    判断顺序：
    1. 是否已登录 → 401
    2. 用户是否存在 → 401
    3. 用户是否处于启用状态 → 403
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    users = load_json("users.json")
    user = users.get(user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="User not found")

    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="User is disabled")

    return user


def require_role(*roles: str):
    """
    返回一个依赖函数，要求当前用户具有指定角色之一。
    使用方式: Depends(require_role("teacher", "admin"))
    """
    async def role_checker(request: Request) -> dict:
        user = await get_current_user(request)
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return role_checker
