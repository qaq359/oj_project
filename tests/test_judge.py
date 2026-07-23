"""
OJ System - Step 2: Python 自动评测测试
"""
import pytest
from app.judge.engine import judge_submission
from app.judge.comparator import normalize, compare


# ---- 测试数据 ----

AC_CODE = "a, b = map(int, input().split())\nprint(a + b)"
WA_CODE = "print(0)"
RE_CODE = "print(1 / 0)"
TLE_CODE = "while True:\n    pass"
EMPTY_CODE = ""

TEST_CASES_SIMPLE = [
    {"case_id": "case_01", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
    {"case_id": "case_02", "input": "-1 2\n", "output": "1\n", "score": 50, "is_hidden": True},
]

TEST_CASES_MULTI = [
    {"case_id": "c1", "input": "10 20\n", "output": "30\n", "score": 30, "is_hidden": False},
    {"case_id": "c2", "input": "0 0\n", "output": "0\n", "score": 30, "is_hidden": False},
    {"case_id": "c3", "input": "100 200\n", "output": "300\n", "score": 40, "is_hidden": False},
]


class TestComparator:
    """输出规范化与比较测试"""

    def test_normalize_newlines(self):
        """统一换行符（\\r\\n → \\n）"""
        assert normalize("1\r\n2\r\n") == "1\n2"

    def test_normalize_cr_only(self):
        """统一 \\r → \\n"""
        assert normalize("1\r2\r") == "1\n2"

    def test_normalize_trailing_spaces(self):
        """删除行末空格"""
        assert normalize("hello   \nworld\t\t\n") == "hello\nworld"

    def test_normalize_trailing_blank_lines(self):
        """删除末尾多余空行"""
        assert normalize("hello\n\n\n\n") == "hello"

    def test_normalize_keep_leading_spaces(self):
        """保留行首空格"""
        assert normalize("  hello\n") == "  hello"

    def test_compare_ac(self):
        """正确输出 → AC"""
        assert compare("3\n", "3\n") is True

    def test_compare_ac_trailing_spaces(self):
        """行末空格不影响 → AC"""
        assert compare("3\n", "3    \n") is True

    def test_compare_wa(self):
        """错误输出 → WA"""
        assert compare("3\n", "0\n") is False


class TestJudgeEngine:
    """评测引擎集成测试"""

    @pytest.mark.asyncio
    async def test_ac(self):
        """正确代码 → AC"""
        result = await judge_submission(AC_CODE, TEST_CASES_SIMPLE, time_limit=2.0)
        assert result["result"] == "AC"
        assert result["score"] == 100
        assert len(result["cases"]) == 2

    @pytest.mark.asyncio
    async def test_wa(self):
        """错误答案 → WA"""
        result = await judge_submission(WA_CODE, TEST_CASES_SIMPLE, time_limit=2.0)
        assert result["result"] == "WA"
        assert result["score"] == 0
        # 第一个测试点就应该 WA
        assert result["cases"][0]["result"] == "WA"

    @pytest.mark.asyncio
    async def test_re(self):
        """运行错误 → RE"""
        result = await judge_submission(RE_CODE, TEST_CASES_SIMPLE, time_limit=2.0)
        assert result["result"] == "RE"
        assert result["score"] == 0

    @pytest.mark.asyncio
    async def test_tle(self):
        """超时代码 → TLE"""
        result = await judge_submission(TLE_CODE, TEST_CASES_SIMPLE, time_limit=0.5)
        assert result["result"] == "TLE"
        assert result["score"] == 0

    @pytest.mark.asyncio
    async def test_empty_code(self):
        """空代码 → SE"""
        result = await judge_submission(EMPTY_CODE, TEST_CASES_SIMPLE, time_limit=1.0)
        assert result["result"] == "SE"
        assert result["score"] == 0

    @pytest.mark.asyncio
    async def test_multi_testcase(self):
        """多测试点计分"""
        result = await judge_submission(AC_CODE, TEST_CASES_MULTI, time_limit=2.0)
        assert result["result"] == "AC"
        assert result["score"] == 100

    @pytest.mark.asyncio
    async def test_partial_score(self):
        """部分得分场景：第一个 AC，第二个 WA"""
        cases = [
            {"case_id": "c1", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
            {"case_id": "c2", "input": "1 2\n", "output": "999\n", "score": 50, "is_hidden": False},
        ]
        result = await judge_submission(AC_CODE, cases, time_limit=2.0)
        # 第一个 AC 得 50，第二个 WA 得 0
        assert result["score"] == 50
        assert result["result"] == "WA"


class TestOutputNormalization:
    """输出规范化边界测试"""

    @pytest.mark.asyncio
    async def test_trailing_spaces_accepted(self):
        """行末空格不影响 AC"""
        code = "print('3    ')"
        cases = [
            {"case_id": "c1", "input": "", "output": "3\n", "score": 100, "is_hidden": False},
        ]
        result = await judge_submission(code, cases, time_limit=2.0)
        assert result["result"] == "AC"
        assert result["score"] == 100

    @pytest.mark.asyncio
    async def test_newline_handling(self):
        """Windows/Linux 换行符兼容：print 在 Windows 输出 \\r\\n，规范化后应匹配"""
        code = "print('hello')\nprint('world')"
        cases = [
            {"case_id": "c1", "input": "", "output": "hello\nworld\n", "score": 100, "is_hidden": False},
        ]
        result = await judge_submission(code, cases, time_limit=2.0)
        assert result["result"] == "AC"
