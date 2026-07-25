"""
OJ System - 代码运行器
在独立子进程中执行学生提交的 Python 代码，
使用 asyncio.to_thread() 避免与 uvicorn 事件循环冲突。
"""
import os
import sys
import shutil
import asyncio
import subprocess
import time
import tempfile


async def run_python_code(
    source_code: str,
    input_data: str,
    time_limit: float,
) -> dict:
    """在线程池中运行子进程，返回 {stdout, stderr, exit_code, time_used, timed_out, error}"""
    run_dir = tempfile.mkdtemp(prefix="oj_", dir=_get_temp_dir())
    code_path = os.path.join(run_dir, "main.py")

    try:
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        python_exe = sys.executable
        start_time = time.perf_counter()

        try:
            result = await asyncio.to_thread(
                _run_subprocess_sync, python_exe, code_path, input_data, time_limit
            )
            elapsed = time.perf_counter() - start_time

            # 二次确认：实际耗时超过限制 → 强制 TLE
            if elapsed >= time_limit and not result["timed_out"]:
                result["timed_out"] = True
                result["exit_code"] = -1

            return {
                "stdout": result["stdout"], "stderr": result["stderr"],
                "exit_code": result["exit_code"], "time_used": round(min(elapsed, time_limit + 5), 4),
                "timed_out": result["timed_out"], "error": None,
            }
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "exit_code": -1,
                    "time_used": 0.0, "timed_out": False, "error": str(e)}
    finally:
        try:
            shutil.rmtree(run_dir, ignore_errors=True)
        except Exception:
            pass


def _run_subprocess_sync(python_exe: str, code_path: str, input_data: str, time_limit: float) -> dict:
    """同步 subprocess（在线程池中运行）"""
    try:
        proc = subprocess.run(
            [python_exe, code_path],
            input=input_data.encode("utf-8"),
            capture_output=True,
            timeout=time_limit,
        )
        stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""

        # Windows: timeout 后进程被 TerminateProcess 杀死，但 subprocess.run 有时
        # 不会抛出 TimeoutExpired，而是正常返回 KeyboardInterrupt + 非零退出码。
        # 检测这种情况 → 强制标记为 TLE
        if "KeyboardInterrupt" in stderr:
            return {"stdout": stdout, "stderr": stderr, "exit_code": -1, "timed_out": True}

        return {"stdout": stdout, "stderr": stderr, "exit_code": proc.returncode, "timed_out": False}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "", "exit_code": -1, "timed_out": True}


def _get_temp_dir() -> str:
    """获取评测临时目录"""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    temp_dir = os.path.join(base, "temp")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir
