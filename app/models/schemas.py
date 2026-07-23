"""
OJ System - Pydantic Schemas / Data Models
"""
from __future__ import annotations
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    UserRole,
    ProblemDifficulty,
    SubmissionStatus,
    JudgeResult,
    JudgeMode,
)


# --- Unified Response ---

class ApiResponse(BaseModel):
    code: int
    message: str = "ok"
    data: object = None


class PaginatedData(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


# --- User Schemas ---

class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: str
    username: str
    role: UserRole
    is_active: bool
    created_at: str
    updated_at: str


class UserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


# --- Problem Schemas ---

class SampleCase(BaseModel):
    input: str
    output: str


class TestCase(BaseModel):
    case_id: str
    input: str
    output: str
    score: int = Field(ge=0)
    is_hidden: bool = False


class ProblemCreate(BaseModel):
    id: str = Field(min_length=1, max_length=32, pattern=r"^[a-zA-Z0-9_\-]+$")
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    input_description: str = Field(min_length=1)
    output_description: str = Field(min_length=1)
    samples: list[SampleCase] = Field(min_length=1)
    constraints: str = ""
    time_limit: float = Field(gt=0)
    memory_limit: int = Field(gt=0)
    difficulty: ProblemDifficulty = ProblemDifficulty.EASY
    tags: list[str] = []
    test_cases: list[TestCase] = Field(min_length=1)
    judge_mode: JudgeMode = JudgeMode.STANDARD


class ProblemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1)
    input_description: str | None = Field(default=None, min_length=1)
    output_description: str | None = Field(default=None, min_length=1)
    samples: list[SampleCase] | None = None
    constraints: str | None = None
    time_limit: float | None = Field(default=None, gt=0)
    memory_limit: int | None = Field(default=None, gt=0)
    difficulty: ProblemDifficulty | None = None
    tags: list[str] | None = None
    test_cases: list[TestCase] | None = None
    judge_mode: JudgeMode | None = None


class ProblemBrief(BaseModel):
    id: str
    title: str
    difficulty: ProblemDifficulty
    tags: list[str]
    time_limit: float
    memory_limit: int


class ProblemDetail(BaseModel):
    id: str
    title: str
    description: str
    input_description: str
    output_description: str
    samples: list[SampleCase]
    constraints: str
    time_limit: float
    memory_limit: int
    difficulty: ProblemDifficulty
    tags: list[str]
    test_cases: list[TestCase] | None = None  # only for teacher/admin


# --- Submission Schemas ---

class SubmissionCreate(BaseModel):
    problem_id: str
    language: str = "python"
    source_code: str = Field(min_length=1, max_length=65536)


class SubmissionBrief(BaseModel):
    submission_id: str
    status: SubmissionStatus


class SubmissionPublic(BaseModel):
    id: str
    user_id: str
    problem_id: str
    language: str
    source_code: str | None = None
    status: SubmissionStatus
    result: JudgeResult | None = None
    score: int = 0
    total_time: float | None = None
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


# --- Judge Log Schemas ---

class CaseLog(BaseModel):
    submission_id: str
    case_id: str
    result: JudgeResult
    score: int
    time_used: float
    memory_used: float | None = None
    exit_code: int
    input_data: str = ""
    stdout: str = ""
    stderr: str = ""
    expected_output: str = ""
    message: str = ""
    is_hidden: bool = False
    created_at: str = ""


class CaseLogStudent(BaseModel):
    case_id: str
    result: JudgeResult
    score: int
    time_used: float
    message: str = ""
    stdout: str | None = None
    expected_output: str | None = None
    is_hidden: bool


# --- Audit Log Schemas ---

class AuditLogEntry(BaseModel):
    id: str
    operator_id: str
    action: str
    target_type: str
    target_id: str
    success: bool
    detail: str | None = None
    created_at: str
