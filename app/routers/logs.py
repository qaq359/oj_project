"""
OJ System - Logs Router
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Query

from app.services import log_service
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(tags=["logs"])


@router.get("/submissions/{submission_id}/logs")
async def get_submission_logs(
    submission_id: str,
    user: dict = Depends(get_current_user),
):
    """获取某次提交的评测日志。学生只能看自己的，教师/管理员可看完整日志。"""
    result = log_service.get_submission_logs(
        submission_id=submission_id,
        viewer_id=user["id"],
        viewer_role=user["role"],
    )
    return {"code": 200, "message": "ok", "data": result}


@router.get("/logs")
async def list_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    submission_id: str | None = Query(default=None),
    problem_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    result: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    user: dict = Depends(require_role("teacher", "admin")),
):
    """教师/管理员日志检索。支持多条件筛选和分页。"""
    data = log_service.list_logs(
        page=page,
        page_size=page_size,
        submission_id=submission_id,
        problem_id=problem_id,
        user_id=user_id,
        result=result,
        start_time=start_time,
        end_time=end_time,
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/audit-logs")
async def list_audit_logs(
    operator_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    user: dict = Depends(require_role("admin")),
):
    """管理员查询审计日志。支持按操作者、动作、目标筛选。"""
    result = log_service.list_audit_logs(
        operator_id=operator_id,
        action=action,
        target_id=target_id,
        start_time=start_time,
        end_time=end_time,
    )
    return {"code": 200, "message": "ok", "data": result}
