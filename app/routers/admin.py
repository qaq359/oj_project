"""
OJ System - Admin Router (Backup & Restore)
"""
from fastapi import APIRouter, Request, HTTPException, Depends

from app.services import admin_service
from app.utils.dependencies import require_role

router = APIRouter(tags=["admin"])


@router.post("/admin/backups", status_code=201)
async def create_backup(
    operator: dict = Depends(require_role("admin")),
):
    """创建数据备份。仅管理员。"""
    result = admin_service.create_backup(operator_id=operator["id"])
    return {"code": 201, "message": "backup created", "data": result}


@router.get("/admin/backups")
async def list_backups(
    operator: dict = Depends(require_role("admin")),
):
    """查询所有备份。仅管理员。"""
    result = admin_service.list_backups()
    return {"code": 200, "message": "ok", "data": result}


@router.post("/admin/backups/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    operator: dict = Depends(require_role("admin")),
):
    """从指定备份恢复数据。仅管理员。恢复后 Session 可能失效。"""
    admin_service.restore_backup(
        backup_id=backup_id,
        operator_id=operator["id"],
    )
    return {"code": 200, "message": "data restored", "data": None}
