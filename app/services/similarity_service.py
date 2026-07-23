"""
OJ System - 代码相似度检测（Adv 3: 进阶模块）
基于 AST 归一化 + 序列比对。
"""
import ast
import uuid
import re
from difflib import SequenceMatcher
from datetime import datetime, timezone

from fastapi import HTTPException

from app.repositories.manager import load_json, save_json
from app.models.enums import UserRole

SIMILARITY_THRESHOLD = 0.7  # 相似度阈值
REPORTS_FILE = "similarity_reports.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ──────────────────── 代码预处理 ────────────────────

def preprocess_code(source: str) -> str:
    """删除空行和注释（包括多行字符串），保留代码结构"""
    # 1. 移除三引号多行字符串（docstring / 多行注释）
    source = _remove_triple_quoted_strings(source)

    # 2. 移除单行注释（保留缩进）
    lines = []
    for line in source.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # 移除行内注释（保留行首缩进）
        if "#" in line:
            line = _remove_inline_comment_preserve_indent(line)
        lines.append(line)
    return "\n".join(lines)


def _remove_inline_comment_preserve_indent(line: str) -> str:
    """移除行内注释，保留行首缩进"""
    in_string = False
    quote_char = ""
    for i, ch in enumerate(line):
        if ch in ('"', "'") and (i == 0 or line[i-1] != "\\"):
            if not in_string:
                in_string = True
                quote_char = ch
            elif ch == quote_char:
                in_string = False
        if ch == "#" and not in_string:
            return line[:i].rstrip()
    return line


def _remove_triple_quoted_strings(source: str) -> str:
    """移除三引号字符串（docstring / 多行注释）"""
    result = []
    i = 0
    in_triple = False
    triple_quote = ""

    while i < len(source):
        if not in_triple:
            # 检查是否遇到三引号开头
            for tq in ('"""', "'''"):
                if source[i:i+3] == tq:
                    in_triple = True
                    triple_quote = tq
                    i += 3
                    break
            if not in_triple:
                result.append(source[i])
                i += 1
        else:
            # 在三引号内，找结束标记
            end_pos = source.find(triple_quote, i)
            if end_pos == -1:
                break  # 未闭合，忽略
            i = end_pos + 3
            in_triple = False
    return "".join(result)


def _remove_inline_comment(line: str) -> str:
    """移除行内注释（简化版）"""
    in_string = False
    quote_char = ""
    for i, ch in enumerate(line):
        if ch in ('"', "'") and (i == 0 or line[i-1] != "\\"):
            if not in_string:
                in_string = True
                quote_char = ch
            elif ch == quote_char:
                in_string = False
        if ch == "#" and not in_string:
            return line[:i].rstrip()
    return line


# ──────────────────── AST 归一化 ────────────────────

class NameNormalizer(ast.NodeTransformer):
    """将 AST 中的变量名、函数名归一化为 var_N 格式"""

    def __init__(self):
        self.name_map = {}
        self.counter = 0

    def _normalize(self, name: str) -> str:
        if name not in self.name_map:
            self.name_map[name] = f"v{self.counter}"
            self.counter += 1
        return self.name_map[name]

    def visit_Name(self, node):
        node.id = self._normalize(node.id)
        return node

    def visit_FunctionDef(self, node):
        node.name = self._normalize(node.name)
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node):
        node.name = self._normalize(node.name)
        self.generic_visit(node)
        return node

    def visit_arg(self, node):
        node.arg = self._normalize(node.arg)
        return node


def ast_fingerprint(source: str) -> str | None:
    """
    对代码做 AST 归一化，返回结构指纹字符串。
    如果代码语法错误则返回 None。
    """
    preprocessed = preprocess_code(source)
    if not preprocessed.strip():
        return None

    try:
        tree = ast.parse(preprocessed)
    except SyntaxError:
        return None

    normalizer = NameNormalizer()
    normalized_tree = normalizer.visit(tree)
    ast.fix_missing_locations(normalized_tree)

    return ast.dump(normalized_tree)


# ──────────────────── 相似度计算 ────────────────────

def calculate_similarity(fp_a: str | None, fp_b: str | None) -> float:
    """计算两个指纹的相似度（0~1）"""
    if fp_a is None or fp_b is None:
        return 0.0
    if fp_a == fp_b:
        return 1.0
    return SequenceMatcher(None, fp_a, fp_b).ratio()


# ──────────────────── 检测服务 ────────────────────

def run_similarity_check(problem_id: str) -> dict:
    """
    对指定题目的所有 Python 提交进行两两相似度比较。
    返回发现的疑似相似对。
    """
    submissions = load_json("submissions.json")
    # 筛选该题目的提交
    problem_subs = {
        sid: s for sid, s in submissions.items()
        if s["problem_id"] == problem_id and s.get("language") == "python"
    }

    if len(problem_subs) < 2:
        raise HTTPException(status_code=400, detail="need at least 2 submissions to compare")

    # 计算所有代码的指纹
    fingerprints = {}
    for sid, s in problem_subs.items():
        fp = ast_fingerprint(s.get("source_code", ""))
        if fp:
            fingerprints[sid] = fp

    # 两两比较
    sid_list = list(fingerprints.keys())
    pairs = []
    now = _now_iso()

    for i in range(len(sid_list)):
        for j in range(i + 1, len(sid_list)):
            sim = calculate_similarity(fingerprints[sid_list[i]], fingerprints[sid_list[j]])
            if sim >= SIMILARITY_THRESHOLD:
                pairs.append({
                    "submission_a": sid_list[i],
                    "submission_b": sid_list[j],
                    "similarity": round(sim, 4),
                    "method": "ast",
                    "created_at": now,
                })

    # 按相似度降序
    pairs.sort(key=lambda p: p["similarity"], reverse=True)

    # 保存报告
    reports = load_json(REPORTS_FILE)
    report_id = str(uuid.uuid4())
    reports[report_id] = {
        "id": report_id,
        "problem_id": problem_id,
        "pairs": pairs,
        "total_pairs": len(pairs),
        "created_at": now,
    }
    save_json(REPORTS_FILE, reports)

    return {"report_id": report_id, "problem_id": problem_id, "total_pairs": len(pairs), "pairs": pairs}


def get_similarity_reports(problem_id: str) -> list[dict]:
    """获取指定题目的所有相似度检测报告"""
    reports = load_json(REPORTS_FILE)
    result = [
        r for r in reports.values()
        if r.get("problem_id") == problem_id
    ]
    result.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return result
