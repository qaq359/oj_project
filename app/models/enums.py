"""
OJ System - Enumerations & Constants
"""
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class ProblemDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SubmissionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"


class JudgeResult(str, Enum):
    AC = "AC"
    WA = "WA"
    RE = "RE"
    TLE = "TLE"
    SE = "SE"


class JudgeMode(str, Enum):
    STANDARD = "standard"
    STRICT = "strict"
    SPJ = "spj"


# 合法状态流转
VALID_STATUS_TRANSITIONS = {
    SubmissionStatus.PENDING: {SubmissionStatus.RUNNING, SubmissionStatus.FAILED},
    SubmissionStatus.RUNNING: {SubmissionStatus.FINISHED, SubmissionStatus.FAILED},
}

# 审计动作
class AuditAction(str, Enum):
    VIEW_FULL_JUDGE_LOG = "VIEW_FULL_JUDGE_LOG"
    REJUDGE_SUBMISSION = "REJUDGE_SUBMISSION"
    UPDATE_USER_ROLE = "UPDATE_USER_ROLE"
    DISABLE_USER = "DISABLE_USER"
    CREATE_BACKUP = "CREATE_BACKUP"
    RESTORE_BACKUP = "RESTORE_BACKUP"
