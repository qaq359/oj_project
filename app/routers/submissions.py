"""
OJ System - Submissions Router
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Query

from app.services import submission_service
from app.utils.dependencies import get_current_user, require_role
from app.models.schemas import SubmissionCreate

router = APIRouter(tags=["submissions"])


@router.post("/submissions", status_code=202)
async def create_submission(
    body: SubmissionCreate,
    user: dict = Depends(get_current_user),
):
    """创建提交。返回 202 + submission_id，后台异步评测。"""
    result = await submission_service.create_submission(
        user_id=user["id"],
        problem_id=body.problem_id,
        language=body.language,
        source_code=body.source_code,
    )
    return {"code": 202, "message": "submission accepted", "data": result}


@router.get("/submissions")
async def list_submissions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    problem_id: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    result: str | None = Query(default=None),
    start_time: str | None = Query(default=None),
    end_time: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
):
    """查询提交列表。学生只能看自己的，教师/管理员可查看全部并筛选。"""
    data = submission_service.list_submissions(
        viewer_id=user["id"],
        viewer_role=user["role"],
        page=page,
        page_size=page_size,
        problem_id=problem_id,
        user_id=user_id,
        status=status,
        result=result,
        start_time=start_time,
        end_time=end_time,
    )
    return {"code": 200, "message": "ok", "data": data}


@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    user: dict = Depends(get_current_user),
):
    """查询单个提交。学生只能看自己的。"""
    result = submission_service.get_submission(
        submission_id=submission_id,
        viewer_id=user["id"],
        viewer_role=user["role"],
    )
    return {"code": 200, "message": "ok", "data": result}


@router.post("/submissions/{submission_id}/rejudge")
async def rejudge_submission(
    submission_id: str,
    operator: dict = Depends(require_role("teacher", "admin")),
):
    """重新评测。仅教师/管理员。只允许 finished/failed 的提交。"""
    await submission_service.rejudge_submission(
        submission_id=submission_id,
        operator_id=operator["id"],
    )
    return {"code": 200, "message": "rejudge initiated", "data": None}
