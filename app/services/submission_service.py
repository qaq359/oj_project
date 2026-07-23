"""
OJ System - 提交与状态管理业务逻辑
"""
import asyncio
import uuid
import traceback
import threading
from datetime import datetime, timezone

from fastapi import HTTPException

from app.repositories.manager import load_json, save_json
from app.judge.engine import judge_submission
from app.models.enums import SubmissionStatus, JudgeResult, UserRole, AuditAction


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ──────────────────── 创建提交 + 异步评测 ────────────────────

async def create_submission(user_id: str, problem_id: str, language: str, source_code: str) -> dict:
    """创建提交记录，立即返回 submission_id，asyncio.create_task 后台评测"""
    problems = load_json("problems.json")
    if problem_id not in problems:
        raise HTTPException(status_code=404, detail="problem not found")

    submission_id = str(uuid.uuid4())
    now = _now_iso()

    submission = {
        "id": submission_id, "user_id": user_id, "problem_id": problem_id,
        "language": language, "source_code": source_code,
        "status": SubmissionStatus.PENDING.value,
        "result": None, "score": 0, "total_time": None,
        "created_at": now, "started_at": None, "finished_at": None,
    }

    submissions = load_json("submissions.json")
    submissions[submission_id] = submission
    save_json("submissions.json", submissions)

    # 用独立线程启动评测（不依赖事件循环，TestClient 中也可靠）
    thread = threading.Thread(
        target=_run_judge_in_thread,
        args=(submission_id, source_code, problem_id),
        daemon=True,
    )
    thread.start()

    return {"submission_id": submission_id, "status": SubmissionStatus.PENDING.value}


def _run_judge_in_thread(submission_id: str, source_code: str, problem_id: str):
    """在线程中运行评测（创建独立事件循环）"""
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run_judge(submission_id, source_code, problem_id))
    finally:
        loop.close()


async def _run_judge(submission_id: str, source_code: str, problem_id: str):
    """后台异步评测任务（通过 asyncio.create_task 调度）"""
    submissions = load_json("submissions.json")
    sub = submissions.get(submission_id)
    if not sub:
        return

    # pending → running
    sub["status"] = SubmissionStatus.RUNNING.value
    sub["started_at"] = _now_iso()
    submissions[submission_id] = sub
    save_json("submissions.json", submissions)

    # 加载题目
    problems = load_json("problems.json")
    problem = problems.get(problem_id, {})
    if not problem:
        _mark_failed(submission_id, "problem not found")
        return

    # 执行评测
    try:
        result = await judge_submission(
            source_code=source_code,
            test_cases=problem.get("test_cases", []),
            time_limit=float(problem.get("time_limit", 1.0)),
        )
    except Exception as e:
        traceback.print_exc()
        result = {"result": JudgeResult.SE.value, "score": 0, "total_time": 0.0,
                  "cases": [{"case_id": "sys", "result": "SE", "score": 0,
                             "time_used": 0.0, "exit_code": -1,
                             "stdout": "", "stderr": str(e)[:500]}]}

    # 更新结果
    submissions = load_json("submissions.json")
    sub = submissions.get(submission_id)
    if sub:
        is_se = result["result"] == JudgeResult.SE.value
        sub["status"] = SubmissionStatus.FAILED.value if is_se else SubmissionStatus.FINISHED.value
        sub["result"] = result["result"]
        sub["score"] = result["score"]
        sub["total_time"] = result["total_time"]
        sub["finished_at"] = _now_iso()
        submissions[submission_id] = sub
        save_json("submissions.json", submissions)

    _save_case_logs(submission_id, problem, result)


def _mark_failed(submission_id: str, message: str):
    """将提交标记为 SE 失败状态（如题目被删除等异常情况）"""
    submissions = load_json("submissions.json")
    sub = submissions.get(submission_id)
    if sub:
        sub["status"] = SubmissionStatus.FAILED.value
        sub["result"] = JudgeResult.SE.value
        sub["score"] = 0
        sub["total_time"] = 0.0
        sub["finished_at"] = _now_iso()
        submissions[submission_id] = sub
        save_json("submissions.json", submissions)
    print(f"[JUDGE] Marked {submission_id} as failed: {message}", flush=True)


def _save_case_logs(submission_id: str, problem: dict, result: dict):
    """保存测试点级别评测日志"""
    logs = load_json("judge_logs.json")
    now = _now_iso()

    for case_result in result.get("cases", []):
        case_id = case_result["case_id"]
        # 找到对应的测试点配置
        tc_config = {}
        for tc in problem.get("test_cases", []):
            if tc["case_id"] == case_id:
                tc_config = tc
                break

        log_entry = {
            "submission_id": submission_id,
            "case_id": case_id,
            "result": case_result["result"],
            "score": case_result["score"],
            "time_used": case_result.get("time_used", 0.0),
            "memory_used": None,
            "exit_code": case_result.get("exit_code", 0),
            "input_data": tc_config.get("input", ""),
            "stdout": case_result.get("stdout", ""),
            "stderr": case_result.get("stderr", ""),
            "expected_output": tc_config.get("output", ""),
            "message": _make_case_message(case_result),
            "is_hidden": tc_config.get("is_hidden", False),
            "created_at": now,
        }
        log_key = f"{submission_id}_{case_id}"
        logs[log_key] = log_entry

    save_json("judge_logs.json", logs)


def _make_case_message(case_result: dict) -> str:
    """生成测试点结果描述信息"""
    r = case_result["result"]
    if r == JudgeResult.AC.value:
        return "accepted"
    elif r == JudgeResult.WA.value:
        return "output does not match expected answer"
    elif r == JudgeResult.TLE.value:
        return "time limit exceeded"
    elif r == JudgeResult.RE.value:
        return f"runtime error (exit code {case_result.get('exit_code', -1)})"
    elif r == JudgeResult.SE.value:
        return "system error"
    return "unknown"


# ──────────────────── 查询 ────────────────────

def list_submissions(
    viewer_id: str,
    viewer_role: str,
    page: int = 1,
    page_size: int = 20,
    problem_id: str | None = None,
    user_id: str | None = None,
    status: str | None = None,
    result: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    """查询提交列表，支持筛选和分页。学生只能看自己的。"""
    submissions = load_json("submissions.json")
    all_items = list(submissions.values())

    # 学生只能看自己的提交
    if viewer_role == UserRole.STUDENT.value:
        all_items = [s for s in all_items if s["user_id"] == viewer_id]

    # 筛选
    if problem_id:
        all_items = [s for s in all_items if s["problem_id"] == problem_id]
    if user_id and viewer_role in (UserRole.TEACHER.value, UserRole.ADMIN.value):
        all_items = [s for s in all_items if s["user_id"] == user_id]
    if status:
        all_items = [s for s in all_items if s["status"] == status]
    if result:
        all_items = [s for s in all_items if s["result"] == result]
    if start_time:
        all_items = [s for s in all_items if s["created_at"] >= start_time]
    if end_time:
        all_items = [s for s in all_items if s["created_at"] <= end_time]

    # 按时间倒序
    all_items.sort(key=lambda s: s["created_at"], reverse=True)

    total = len(all_items)
    start = (page - 1) * page_size
    end = start + page_size
    items = [_submission_to_public(s, viewer_id == s["user_id"]) for s in all_items[start:end]]

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_submission(submission_id: str, viewer_id: str, viewer_role: str) -> dict:
    """获取单个提交详情。学生只能看自己的。"""
    submissions = load_json("submissions.json")
    if submission_id not in submissions:
        raise HTTPException(status_code=404, detail="submission not found")

    sub = submissions[submission_id]

    # 权限检查
    is_admin = viewer_role in (UserRole.TEACHER.value, UserRole.ADMIN.value)
    if not is_admin and sub["user_id"] != viewer_id:
        raise HTTPException(status_code=403, detail="access denied")

    is_owner = sub["user_id"] == viewer_id
    return _submission_to_public(sub, is_owner)


def _submission_to_public(sub: dict, include_source: bool = False) -> dict:
    """将内部存储的提交转为对外格式"""
    result = {
        "id": sub["id"],
        "user_id": sub["user_id"],
        "problem_id": sub["problem_id"],
        "language": sub.get("language", "python"),
        "source_code": sub.get("source_code") if include_source else None,
        "status": sub["status"],
        "result": sub.get("result"),
        "score": sub.get("score", 0),
        "total_time": sub.get("total_time"),
        "created_at": sub.get("created_at", ""),
        "started_at": sub.get("started_at"),
        "finished_at": sub.get("finished_at"),
    }
    return result


# ──────────────────── 重新评测 ────────────────────

async def rejudge_submission(submission_id: str, operator_id: str) -> None:
    """重新评测。仅教师/管理员。只允许 finished/failed 的提交。"""
    submissions = load_json("submissions.json")

    if submission_id not in submissions:
        raise HTTPException(status_code=404, detail="submission not found")

    sub = submissions[submission_id]

    # 状态检查
    allowed = {SubmissionStatus.FINISHED.value, SubmissionStatus.FAILED.value}
    if sub["status"] not in allowed:
        raise HTTPException(status_code=409, detail=f"cannot rejudge submission in '{sub['status']}' status")

    # 重置为 pending
    sub["status"] = SubmissionStatus.PENDING.value
    sub["result"] = None
    sub["score"] = 0
    sub["total_time"] = None
    sub["started_at"] = None
    sub["finished_at"] = None
    submissions[submission_id] = sub
    save_json("submissions.json", submissions)

    # 删除旧日志
    _clear_case_logs(submission_id)

    # 写入审计日志
    _write_audit_log(operator_id, AuditAction.REJUDGE_SUBMISSION.value, "submission", submission_id)

    # 用独立线程重新启动评测
    thread = threading.Thread(
        target=_run_judge_in_thread,
        args=(submission_id, sub["source_code"], sub["problem_id"]),
        daemon=True,
    )
    thread.start()


def _clear_case_logs(submission_id: str):
    """清除指定提交的旧测试点日志"""
    logs = load_json("judge_logs.json")
    keys_to_delete = [k for k in logs if k.startswith(f"{submission_id}_")]
    for k in keys_to_delete:
        del logs[k]
    save_json("judge_logs.json", logs)


def _write_audit_log(operator_id: str, action: str, target_type: str, target_id: str):
    """写入审计日志"""
    logs = load_json("audit_logs.json")
    log_id = str(uuid.uuid4())
    logs[log_id] = {
        "id": log_id,
        "operator_id": operator_id,
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "success": True,
        "detail": None,
        "created_at": _now_iso(),
    }
    save_json("audit_logs.json", logs)
