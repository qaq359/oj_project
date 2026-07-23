"""
OJ System - 评测日志业务逻辑
"""
from fastapi import HTTPException

from app.repositories.manager import load_json
from app.models.enums import UserRole, AuditAction
from app.utils.sanitizers import to_student_log, to_teacher_log
from app.services.submission_service import _write_audit_log


def get_submission_logs(submission_id: str, viewer_id: str, viewer_role: str) -> dict:
    """
    获取某次提交的评测日志。
    学生：只能看自己的，隐藏测试点输入/答案，路径脱敏
    教师/管理员：完整日志，查看时写入审计记录
    """
    submissions = load_json("submissions.json")
    if submission_id not in submissions:
        raise HTTPException(status_code=404, detail="submission not found")

    sub = submissions[submission_id]
    is_admin = viewer_role in (UserRole.TEACHER.value, UserRole.ADMIN.value)

    # 权限检查
    if not is_admin and sub["user_id"] != viewer_id:
        raise HTTPException(status_code=403, detail="access denied")

    # 加载测试点日志
    all_logs = load_json("judge_logs.json")
    case_logs = []
    for key, log in all_logs.items():
        if key.startswith(f"{submission_id}_"):
            case_logs.append(log)

    # 按 case_id 排序
    case_logs.sort(key=lambda l: l.get("case_id", ""))

    # 构造摘要
    summary = {
        "submission_id": submission_id,
        "problem_id": sub["problem_id"],
        "status": sub["status"],
        "result": sub.get("result"),
        "score": sub.get("score", 0),
        "total_time": sub.get("total_time"),
    }

    if is_admin:
        # 教师/管理员：完整日志
        details = [to_teacher_log(log) for log in case_logs]
        # 写入审计日志
        _write_audit_log(viewer_id, AuditAction.VIEW_FULL_JUDGE_LOG.value,
                         "submission", submission_id)
    else:
        # 学生：脱敏日志
        details = [to_student_log(log) for log in case_logs]

    return {"summary": summary, "cases": details}


def list_logs(
    page: int = 1,
    page_size: int = 20,
    submission_id: str | None = None,
    problem_id: str | None = None,
    user_id: str | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    """
    教师/管理员日志检索。
    基于提交记录 + 关联的测试点日志进行筛选。
    """
    submissions = load_json("submissions.json")
    all_subs = list(submissions.values())

    # 筛选
    if submission_id:
        all_subs = [s for s in all_subs if s["id"] == submission_id]
    if problem_id:
        all_subs = [s for s in all_subs if s["problem_id"] == problem_id]
    if user_id:
        all_subs = [s for s in all_subs if s["user_id"] == user_id]
    if result:
        all_subs = [s for s in all_subs if s.get("result") == result]
    if start_time:
        all_subs = [s for s in all_subs if s["created_at"] >= start_time]
    if end_time:
        all_subs = [s for s in all_subs if s["created_at"] <= end_time]

    all_subs.sort(key=lambda s: s["created_at"], reverse=True)

    total = len(all_subs)
    start = (page - 1) * page_size
    end = start + page_size

    # 加载日志，附加到每个提交
    all_logs = load_json("judge_logs.json")
    items = []
    for s in all_subs[start:end]:
        cases = []
        for key, log in all_logs.items():
            if key.startswith(f"{s['id']}_"):
                cases.append(to_teacher_log(log))
        items.append({
            "submission": {
                "id": s["id"],
                "user_id": s["user_id"],
                "problem_id": s["problem_id"],
                "status": s["status"],
                "result": s.get("result"),
                "score": s.get("score", 0),
                "total_time": s.get("total_time"),
                "created_at": s.get("created_at", ""),
            },
            "cases": cases,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_audit_logs(
    operator_id: str | None = None,
    action: str | None = None,
    target_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> list[dict]:
    """管理员查询审计日志，支持按操作者、动作、目标、时间筛选"""
    logs = load_json("audit_logs.json")
    all_items = list(logs.values())

    if operator_id:
        all_items = [l for l in all_items if l.get("operator_id") == operator_id]
    if action:
        all_items = [l for l in all_items if l.get("action") == action]
    if target_id:
        all_items = [l for l in all_items if l.get("target_id") == target_id]
    if start_time:
        all_items = [l for l in all_items if l.get("created_at", "") >= start_time]
    if end_time:
        all_items = [l for l in all_items if l.get("created_at", "") <= end_time]

    all_items.sort(key=lambda l: l.get("created_at", ""), reverse=True)

    # 审计日志本身也需要脱敏（截断 detail）
    for item in all_items:
        if item.get("detail") and len(item["detail"]) > 1000:
            item["detail"] = item["detail"][:1000] + "...[truncated]"

    return all_items
