"""
OJ System - 日志脱敏与截断工具
"""
import os
import re

MAX_FIELD_LENGTH = 4000
TRUNCATED_MARKER = "...[truncated]"


def truncate_text(text: str, max_length: int = MAX_FIELD_LENGTH) -> str:
    """截断超长文本，超过限制时在末尾追加标记。统计 Unicode 字符数。"""
    if not text:
        return text
    if len(text) <= max_length:
        return text
    return text[:max_length] + TRUNCATED_MARKER


def sanitize_path(text: str) -> str:
    """脱敏服务器绝对路径，替换为 <submission>/main.py 或友好提示。"""
    if not text:
        return text
    # Windows: C:\...\temp\oj_xxx\main.py
    # Linux:   /home/.../temp/oj_xxx/main.py
    # 匹配常见的绝对路径模式
    patterns = [
        (r'[A-Za-z]:[\\/][^ \n]*?temp[\\/]oj_[^ \n]*?main\.py', '<submission>/main.py'),
        (r'/[^ \n]*?temp/oj_[^ \n]*?main\.py', '<submission>/main.py'),
        (r'[A-Za-z]:[\\/][^ \n]*?oj_project[\\/]', '<project>/'),
        (r'/[^ \n]*?oj_project/', '<project>/'),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def truncate_log_entry(log: dict) -> dict:
    """对日志条目中的长文本字段执行截断"""
    fields_to_truncate = ["input_data", "stdout", "stderr", "expected_output"]
    for field in fields_to_truncate:
        if field in log:
            log[field] = truncate_text(log.get(field, ""))
    if "message" in log:
        log["message"] = truncate_text(log.get("message", ""), max_length=1000)
    return log


def to_student_log(log: dict) -> dict:
    """
    将完整日志转为学生可看版本。
    移除：隐藏测试点的 input/stdout/expected_output
    脱敏：路径
    截断：长文本
    保留：case_id, result, score, time_used, message, 非隐藏的 stdout/expected_output
    """
    log = dict(log)  # 不修改原数据
    is_hidden = log.get("is_hidden", False)

    result = {
        "case_id": log.get("case_id", ""),
        "result": log.get("result", ""),
        "score": log.get("score", 0),
        "time_used": log.get("time_used", 0.0),
        "message": truncate_text(sanitize_path(log.get("message", "")), 1000),
        "is_hidden": is_hidden,
    }

    # 非隐藏测试点：可以看到 stdout 和 expected_output
    if not is_hidden:
        result["stdout"] = truncate_text(sanitize_path(log.get("stdout", "")))
        result["expected_output"] = truncate_text(log.get("expected_output", ""))
    else:
        result["stdout"] = None
        result["expected_output"] = None

    # stderr 始终显示（但经过脱敏和截断）
    result["stderr"] = truncate_text(sanitize_path(log.get("stderr", "")))

    return result


def to_teacher_log(log: dict) -> dict:
    """
    教师/管理员看到的完整日志。
    仍然对长文本执行截断（4000字符），路径脱敏。
    """
    log = dict(log)
    log = truncate_log_entry(log)
    if "stderr" in log:
        log["stderr"] = sanitize_path(log["stderr"])
    if "stdout" in log:
        log["stdout"] = sanitize_path(log["stdout"])
    return log
