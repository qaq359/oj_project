"""
OJ System - 题目管理业务逻辑
"""
from fastapi import HTTPException

from app.repositories.manager import load_json, save_json
from app.models.enums import UserRole


def _serialize_test_case(tc: dict) -> dict:
    """序列化测试点，确保数据类型正确"""
    return {
        "case_id": str(tc["case_id"]),
        "input": str(tc["input"]),
        "output": str(tc["output"]),
        "score": int(tc["score"]),
        "is_hidden": bool(tc.get("is_hidden", False)),
    }


def _validate_test_cases(test_cases: list[dict]) -> None:
    """校验测试点：非空、分值总和=100"""
    if not test_cases:
        raise HTTPException(status_code=422, detail="test_cases must not be empty")
    total = sum(int(tc["score"]) for tc in test_cases)
    if total != 100:
        raise HTTPException(status_code=422, detail=f"test_cases total score must be 100, got {total}")


def _problem_to_brief(p: dict) -> dict:
    """将内部存储的题目转为列表摘要"""
    return {
        "id": p["id"],
        "title": p["title"],
        "difficulty": p.get("difficulty", "easy"),
        "tags": p.get("tags", []),
        "time_limit": p.get("time_limit", 1.0),
        "memory_limit": p.get("memory_limit", 128),
    }


def _problem_to_detail(p: dict, include_test_cases: bool = False) -> dict:
    """将内部存储的题目转为详情"""
    detail = {
        "id": p["id"],
        "title": p["title"],
        "description": p["description"],
        "input_description": p.get("input_description", ""),
        "output_description": p.get("output_description", ""),
        "samples": p.get("samples", []),
        "constraints": p.get("constraints", ""),
        "time_limit": p.get("time_limit", 1.0),
        "memory_limit": p.get("memory_limit", 128),
        "difficulty": p.get("difficulty", "easy"),
        "tags": p.get("tags", []),
        "test_cases": p.get("test_cases", []) if include_test_cases else None,
    }
    return detail


def list_problems(role: str) -> list[dict]:
    """获取题目列表。学生只能看到公开信息。"""
    problems = load_json("problems.json")
    return [_problem_to_brief(p) for p in problems.values()]


def get_problem(problem_id: str, role: str) -> dict:
    """获取单个题目详情。教师/管理员可看测试点，学生不可。"""
    problems = load_json("problems.json")
    if problem_id not in problems:
        raise HTTPException(status_code=404, detail="problem not found")

    p = problems[problem_id]
    include_tc = role in (UserRole.TEACHER.value, UserRole.ADMIN.value)
    return _problem_to_detail(p, include_test_cases=include_tc)


def create_problem(data: dict) -> dict:
    """创建题目。校验字段和测试点后写入持久化存储。"""
    problems = load_json("problems.json")

    # 题号重复检查
    problem_id = data["id"]
    if problem_id in problems:
        raise HTTPException(status_code=409, detail="problem id already exists")

    # 测试点校验
    test_cases_raw = data.get("test_cases", [])
    _validate_test_cases(test_cases_raw)

    # 构造题目对象
    problem = {
        "id": problem_id,
        "title": data["title"],
        "description": data["description"],
        "input_description": data.get("input_description", ""),
        "output_description": data.get("output_description", ""),
        "samples": [{"input": s["input"], "output": s["output"]} for s in data.get("samples", [])],
        "constraints": data.get("constraints", ""),
        "time_limit": float(data.get("time_limit", 1.0)),
        "memory_limit": int(data.get("memory_limit", 128)),
        "difficulty": data.get("difficulty", "easy"),
        "tags": data.get("tags", []),
        "test_cases": [_serialize_test_case(tc) for tc in test_cases_raw],
        "judge_mode": data.get("judge_mode", "standard"),
    }

    problems[problem_id] = problem
    save_json("problems.json", problems)
    return _problem_to_detail(problem, include_test_cases=True)


def update_problem(problem_id: str, data: dict) -> dict:
    """修改题目。不允许修改题号，修改后仍需通过完整校验。"""
    problems = load_json("problems.json")

    if problem_id not in problems:
        raise HTTPException(status_code=404, detail="problem not found")

    existing = problems[problem_id]

    # 只更新提供的字段（排除 id）
    update_fields = {k: v for k, v in data.items() if v is not None and k != "id"}
    if not update_fields:
        raise HTTPException(status_code=400, detail="no fields to update")

    # 如果传了 test_cases，需要校验
    if "test_cases" in update_fields:
        _validate_test_cases(update_fields["test_cases"])
        update_fields["test_cases"] = [_serialize_test_case(tc) for tc in update_fields["test_cases"]]

    # 如果传了 samples，确保格式正确
    if "samples" in update_fields:
        update_fields["samples"] = [
            {"input": s["input"], "output": s["output"]} for s in update_fields["samples"]
        ]

    # 合并更新
    existing.update(update_fields)

    problems[problem_id] = existing
    save_json("problems.json", problems)
    return _problem_to_detail(existing, include_test_cases=True)


def delete_problem(problem_id: str) -> None:
    """删除题目。已有关联提交的历史记录不被级联删除。"""
    problems = load_json("problems.json")

    if problem_id not in problems:
        raise HTTPException(status_code=404, detail="problem not found")

    del problems[problem_id]
    save_json("problems.json", problems)
