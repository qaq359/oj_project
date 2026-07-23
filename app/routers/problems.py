"""
OJ System - Problems Router
"""
from fastapi import APIRouter, Request, HTTPException, Depends, Query

from app.utils.dependencies import get_current_user, require_role
from app.services import problem_service
from app.services import similarity_service
from app.models.schemas import ProblemCreate, ProblemUpdate

router = APIRouter(tags=["problems"])


@router.get("/problems")
async def list_problems(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """获取题目列表。学生/教师/管理员均可访问，学生看不到 test_cases。"""
    result = problem_service.list_problems(role=user["role"])
    return {
        "code": 200,
        "message": "ok",
        "data": {"items": result, "total": len(result), "page": 1, "page_size": len(result)},
    }


@router.get("/problems/{problem_id}")
async def get_problem(
    problem_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """获取题目详情。教师/管理员可查看完整测试点，学生不可。"""
    result = problem_service.get_problem(problem_id, role=user["role"])
    return {"code": 200, "message": "ok", "data": result}


@router.post("/problems", status_code=201)
async def create_problem(
    body: ProblemCreate,
    request: Request,
    user: dict = Depends(require_role("teacher", "admin")),
):
    """创建题目。仅教师和管理员有权限。"""
    result = problem_service.create_problem(body.model_dump())
    return {"code": 201, "message": "problem created", "data": result}


@router.put("/problems/{problem_id}")
async def update_problem(
    problem_id: str,
    body: ProblemUpdate,
    request: Request,
    user: dict = Depends(require_role("teacher", "admin")),
):
    """修改题目。不允许修改题号，修改后仍需通过完整校验。"""
    result = problem_service.update_problem(problem_id, body.model_dump(exclude_none=True))
    return {"code": 200, "message": "problem updated", "data": result}


@router.delete("/problems/{problem_id}")
async def delete_problem(
    problem_id: str,
    request: Request,
    user: dict = Depends(require_role("teacher", "admin")),
):
    """删除题目。已有提交记录不被级联删除。"""
    problem_service.delete_problem(problem_id)
    return {"code": 200, "message": "problem deleted", "data": None}


# ──────── Adv 3: 代码相似度检测 ────────

@router.post("/problems/{problem_id}/similarity-check")
async def check_similarity(
    problem_id: str,
    user: dict = Depends(require_role("teacher", "admin")),
):
    """对指定题目的所有提交进行相似度分析。仅教师/管理员。"""
    result = similarity_service.run_similarity_check(problem_id)
    return {"code": 200, "message": "similarity check completed", "data": result}


@router.get("/problems/{problem_id}/similarity-reports")
async def get_similarity_reports(
    problem_id: str,
    user: dict = Depends(require_role("teacher", "admin")),
):
    """获取指定题目的历史相似度检测报告。仅教师/管理员。"""
    result = similarity_service.get_similarity_reports(problem_id)
    return {"code": 200, "message": "ok", "data": result}
