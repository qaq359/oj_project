"""
OJ System - Users Router
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Query

from app.services import user_service
from app.utils.dependencies import require_role
from app.models.schemas import UserUpdate

router = APIRouter(tags=["users"])


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(require_role("admin")),
):
    """获取用户分页列表。仅管理员。"""
    result = user_service.list_users(page=page, page_size=page_size)
    return {"code": 200, "message": "ok", "data": result}


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    admin_user: dict = Depends(require_role("admin")),
):
    """获取单个用户信息。仅管理员。"""
    result = user_service.get_user(user_id)
    return {"code": 200, "message": "ok", "data": result}


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdate,
    operator: dict = Depends(require_role("admin")),
):
    """修改用户角色或启用状态。仅管理员，不能禁用自己。"""
    result = user_service.update_user(
        operator_id=operator["id"],
        target_id=user_id,
        role=body.role.value if body.role else None,
        is_active=body.is_active,
    )
    return {"code": 200, "message": "user updated", "data": result}
