"""
OJ System - 评测引擎
负责编排整个评测流程：逐测试点运行、比较、计分、汇总。
"""
import asyncio

from app.judge.runner import run_python_code
from app.judge.comparator import compare
from app.models.enums import JudgeResult


async def judge_submission(
    source_code: str,
    test_cases: list[dict],
    time_limit: float,
) -> dict:
    """
    对一份提交执行完整评测。

    Args:
        source_code: 学生源代码
        test_cases: 测试点列表 [{"case_id", "input", "output", "score", "is_hidden"}, ...]
        time_limit: 每题的时间限制（秒）

    Returns:
        {
            "result": "AC"|"WA"|"RE"|"TLE"|"SE",
            "score": int,
            "total_time": float,
            "cases": [{每个测试点的详细结果}]
        }
    """
    # 空代码直接返回 SE
    if not source_code or not source_code.strip():
        return _make_se_result("Empty source code", test_cases)

    case_results = []
    total_score = 0
    total_time = 0.0
    stop_judging = False

    for tc in test_cases:
        if stop_judging:
            break

        # 运行代码
        run_result = await run_python_code(
            source_code=source_code,
            input_data=tc["input"],
            time_limit=time_limit,
        )

        # 判断结果
        case_entry = _evaluate_case(tc, run_result)
        case_results.append(case_entry)
        total_time += case_entry["time_used"]
        total_score += case_entry["score"]

        # 遇到非 AC 时停止后续评测（一致行为）
        if case_entry["result"] != JudgeResult.AC.value:
            stop_judging = True

    # 汇总最终结果
    final_result = _determine_final_result(case_results)

    return {
        "result": final_result,
        "score": total_score,
        "total_time": round(total_time, 4),
        "cases": case_results,
    }


def _evaluate_case(tc: dict, run_result: dict) -> dict:
    """
    评估单个测试点的结果。

    判断优先级：
    1. timed_out → TLE
    2. exit_code != 0 → RE
    3. run_result["error"] → SE
    4. 输出比较失败 → WA
    5. 否则 → AC
    """
    case_id = tc["case_id"]
    score = int(tc.get("score", 0))

    # TLE
    if run_result["timed_out"]:
        return {
            "case_id": case_id,
            "result": JudgeResult.TLE.value,
            "score": 0,
            "time_used": run_result["time_used"],
            "exit_code": run_result["exit_code"],
            "stdout": run_result["stdout"],
            "stderr": run_result["stderr"],
        }

    # SE (runner error)
    if run_result.get("error"):
        return {
            "case_id": case_id,
            "result": JudgeResult.SE.value,
            "score": 0,
            "time_used": run_result["time_used"],
            "exit_code": run_result["exit_code"],
            "stdout": run_result["stdout"],
            "stderr": str(run_result["error"])[:500],
        }

    # RE (non-zero exit code)
    if run_result["exit_code"] != 0:
        return {
            "case_id": case_id,
            "result": JudgeResult.RE.value,
            "score": 0,
            "time_used": run_result["time_used"],
            "exit_code": run_result["exit_code"],
            "stdout": run_result["stdout"],
            "stderr": run_result["stderr"],
        }

    # Output comparison
    passed = compare(tc["output"], run_result["stdout"])
    if not passed:
        return {
            "case_id": case_id,
            "result": JudgeResult.WA.value,
            "score": 0,
            "time_used": run_result["time_used"],
            "exit_code": run_result["exit_code"],
            "stdout": run_result["stdout"],
            "stderr": run_result["stderr"],
        }

    # AC
    return {
        "case_id": case_id,
        "result": JudgeResult.AC.value,
        "score": score,
        "time_used": run_result["time_used"],
        "exit_code": 0,
        "stdout": run_result["stdout"],
        "stderr": run_result["stderr"],
    }


def _determine_final_result(case_results: list[dict]) -> str:
    """
    根据所有测试点结果确定最终结果。
    优先级：SE > TLE > RE > WA > AC
    """
    if not case_results:
        return JudgeResult.SE.value

    has_se = any(c["result"] == JudgeResult.SE.value for c in case_results)
    has_tle = any(c["result"] == JudgeResult.TLE.value for c in case_results)
    has_re = any(c["result"] == JudgeResult.RE.value for c in case_results)
    has_wa = any(c["result"] == JudgeResult.WA.value for c in case_results)

    if has_se:
        return JudgeResult.SE.value
    if has_tle:
        return JudgeResult.TLE.value
    if has_re:
        return JudgeResult.RE.value
    if has_wa:
        return JudgeResult.WA.value
    return JudgeResult.AC.value


def _make_se_result(message: str, test_cases: list[dict]) -> dict:
    """构造评测系统错误的结果"""
    return {
        "result": JudgeResult.SE.value,
        "score": 0,
        "total_time": 0.0,
        "cases": [
            {
                "case_id": tc["case_id"],
                "result": JudgeResult.SE.value,
                "score": 0,
                "time_used": 0.0,
                "exit_code": -1,
                "stdout": "",
                "stderr": message,
            }
            for tc in test_cases
        ],
    }
