import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class UserRead(ORMModel):
    id: uuid.UUID
    email: EmailStr
    username: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ResumeProfile(BaseModel):
    name: str = ""
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    experience: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    interview_points: list[str] = Field(default_factory=list)


class JDRequirements(BaseModel):
    title: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)


class ResumeRead(ORMModel):
    id: uuid.UUID
    original_name: str
    status: str
    profile_json: dict
    error_message: str | None
    created_at: datetime


class JDRead(ORMModel):
    id: uuid.UUID
    title: str
    status: str
    requirements_json: dict
    error_message: str | None
    created_at: datetime


class JobRead(ORMModel):
    id: uuid.UUID
    job_type: str
    status: str
    progress: int
    result_json: dict
    error_message: str | None
    created_at: datetime


class MatchResult(BaseModel):
    score: float = Field(ge=0, le=100)
    required_coverage: float = Field(ge=0, le=1)
    preferred_coverage: float = Field(ge=0, le=1)
    matched_skills: list[str]
    missing_required_skills: list[str]
    missing_preferred_skills: list[str]
    strengths: list[str]
    risks: list[str]
    preparation_priority: list[str]


class InterviewCreate(BaseModel):
    resume_id: uuid.UUID
    jd_id: uuid.UUID
    max_questions: int = Field(default=5, ge=1, le=20)


class AnswerCreate(BaseModel):
    answer: str = Field(min_length=2, max_length=10000)


class AnswerScore(BaseModel):
    technical_accuracy: float = Field(ge=0, le=5)
    project_depth: float = Field(ge=0, le=5)
    communication: float = Field(ge=0, le=5)
    job_fit: float = Field(ge=0, le=5)
    total: float = Field(ge=0, le=20)
    evidence: list[str] = Field(default_factory=list)
    missing_points: list[str] = Field(default_factory=list)
    feedback: str
    needs_followup: bool


class GeneratedQuestion(BaseModel):
    question: str
    question_type: str
    why_asked: str
    expected_points: list[str]
    source_chunk_ids: list[str] = Field(default_factory=list)


class InterviewRead(ORMModel):
    id: uuid.UUID
    status: str
    max_questions: int
    answered_questions: int
    current_question: str | None
    current_question_type: str | None
    match_score: float
    match_result_json: dict
    created_at: datetime


class MessageRead(ORMModel):
    id: uuid.UUID
    sequence_no: int
    role: str
    message_type: str
    content: str
    score_json: dict
    meta_json: dict
    created_at: datetime


class ReportRead(ORMModel):
    id: uuid.UUID
    session_id: uuid.UUID
    overall_score: float
    report_json: dict
    report_path: str | None
