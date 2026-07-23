"""
OJ System - 输出比较器
实现输出规范化与比较逻辑。
"""
import re


def normalize(text: str) -> str:
    """
    规范化输出文本，用于评测比较。
    规则：
    1. 将 \\r\\n 和 \\r 统一转换为 \\n
    2. 删除每行末尾的空格和制表符
    3. 删除文件末尾多余的空行
    4. 不忽略行首空格
    5. 不忽略行内空格
    """
    # 1. 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. 删除每行末尾空格/制表符
    lines = text.split("\n")
    lines = [line.rstrip(" \t") for line in lines]

    # 3. 删除末尾多余空行
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def compare(expected: str, actual: str) -> bool:
    """
    比较规范化后的实际输出与期望输出。
    返回 True 表示匹配（AC），False 表示不匹配（WA）。
    """
    norm_expected = normalize(expected)
    norm_actual = normalize(actual)
    return norm_expected == norm_actual
