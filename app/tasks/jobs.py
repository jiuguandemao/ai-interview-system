import json
import traceback
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.config import get_settings
from app.database import SessionLocal
from app.models import (
    AsyncJob,
    InterviewMessage,
    InterviewReport,
    InterviewSession,
    JobDescription,
    Resume,
)
from app.schemas import JDRequirements, ResumeProfile
from app.services.agent_graph import build_interview_graph
from app.services.file_parser import extract_text
from app.services.llm import LLMService
from app.services.matching import calculate_match
from app.services.rag import RAGService
from app.services.question_bank import ensure_default_question_bank
from app.services.report import build_report
from app.tasks.celery_app import celery_app


settings = get_settings()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def mark_started(db, job: AsyncJob, progress: int = 5) -> None:
    job.status = "running"
    job.progress = progress
    job.started_at = utc_now()
    db.commit()


def mark_success(db, job: AsyncJob, result: dict) -> None:
    job.status = "success"
    job.progress = 100
    job.result_json = result
    job.finished_at = utc_now()
    db.commit()


def mark_failed(db, job_id: uuid.UUID, exc: Exception) -> None:
    db.rollback()
    job = db.get(AsyncJob, job_id)
    if job:
        job.status = "failed"
        job.error_message = f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=5)}"
        job.finished_at = utc_now()
        db.commit()


def next_sequence(db, session_id: uuid.UUID) -> int:
    current = db.scalar(
        select(func.coalesce(func.max(InterviewMessage.sequence_no), 0)).where(
            InterviewMessage.session_id == session_id
        )
    )
    return int(current or 0) + 1


@celery_app.task(name="documents.parse_resume")
def parse_resume_task(job_id: str, resume_id: str) -> dict:
    job_uuid, resume_uuid = uuid.UUID(job_id), uuid.UUID(resume_id)
    with SessionLocal() as db:
        job = db.get(AsyncJob, job_uuid)
        resume = db.get(Resume, resume_uuid)
        if not job or not resume:
            raise ValueError("任务或简历记录不存在")
        try:
            mark_started(db, job)
            resume.status = "processing"
            db.commit()
            text = extract_text(resume.file_path)
            job.progress = 35
            db.commit()
            profile = LLMService().extract_resume(text)
            resume.raw_text = text
            resume.profile_json = profile.model_dump()
            job.progress = 65
            db.commit()
            RAGService().index_document(
                db,
                user_id=resume.user_id,
                source_type="resume",
                source_id=resume.id,
                title=resume.original_name,
                text=text,
                metadata={"resume_id": str(resume.id)},
            )
            resume.status = "ready"
            db.commit()
            result = {"resume_id": str(resume.id), "skills": profile.skills}
            mark_success(db, job, result)
            return result
        except Exception as exc:
            db.rollback()
            resume = db.get(Resume, resume_uuid)
            if resume:
                resume.status = "failed"
                resume.error_message = str(exc)
                db.commit()
            mark_failed(db, job_uuid, exc)
            raise


@celery_app.task(name="documents.parse_jd")
def parse_jd_task(job_id: str, jd_id: str) -> dict:
    job_uuid, jd_uuid = uuid.UUID(job_id), uuid.UUID(jd_id)
    with SessionLocal() as db:
        job = db.get(AsyncJob, job_uuid)
        jd = db.get(JobDescription, jd_uuid)
        if not job or not jd:
            raise ValueError("任务或 JD 记录不存在")
        try:
            mark_started(db, job)
            jd.status = "processing"
            db.commit()
            text = extract_text(jd.file_path) if jd.file_path else jd.raw_text
            requirements = LLMService().extract_jd(text, jd.title)
            jd.raw_text = text
            jd.requirements_json = requirements.model_dump()
            job.progress = 65
            db.commit()
            RAGService().index_document(
                db,
                user_id=jd.user_id,
                source_type="jd",
                source_id=jd.id,
                title=jd.title,
                text=text,
                metadata={"jd_id": str(jd.id)},
            )
            jd.status = "ready"
            db.commit()
            result = {"jd_id": str(jd.id), "required_skills": requirements.required_skills}
            mark_success(db, job, result)
            return result
        except Exception as exc:
            db.rollback()
            jd = db.get(JobDescription, jd_uuid)
            if jd:
                jd.status = "failed"
                jd.error_message = str(exc)
                db.commit()
            mark_failed(db, job_uuid, exc)
            raise


@celery_app.task(name="interviews.prepare")
def prepare_interview_task(job_id: str, session_id: str) -> dict:
    job_uuid, session_uuid = uuid.UUID(job_id), uuid.UUID(session_id)
    with SessionLocal() as db:
        job = db.get(AsyncJob, job_uuid)
        interview = db.get(InterviewSession, session_uuid)
        if not job or not interview:
            raise ValueError("任务或面试会话不存在")
        try:
            mark_started(db, job)
            resume = db.get(Resume, interview.resume_id)
            jd = db.get(JobDescription, interview.jd_id)
            profile = ResumeProfile.model_validate(resume.profile_json)
            requirements = JDRequirements.model_validate(jd.requirements_json)
            match = calculate_match(profile, requirements)
            interview.match_score = match.score
            interview.match_result_json = match.model_dump()
            job.progress = 45
            db.commit()

            ensure_default_question_bank(db, interview.user_id)

            initial_state = {
                "phase": "start",
                "user_id": str(interview.user_id),
                "profile": profile.model_dump(),
                "jd": requirements.model_dump(),
                "answered_count": 0,
            }
            state = build_interview_graph(db).invoke(initial_state)
            interview.current_question = state["question"]
            interview.current_question_type = state["question_type"]
            interview.agent_state_json = {
                "context": state.get("context", []),
                "expected_points": state.get("expected_points", []),
                "source_chunk_ids": state.get("source_chunk_ids", []),
            }
            interview.status = "active"
            db.add(
                InterviewMessage(
                    session_id=interview.id,
                    sequence_no=next_sequence(db, interview.id),
                    role="interviewer",
                    message_type=interview.current_question_type or "question",
                    content=interview.current_question,
                    meta_json={"source_chunk_ids": state.get("source_chunk_ids", [])},
                )
            )
            db.commit()
            result = {"session_id": str(interview.id), "question": interview.current_question}
            mark_success(db, job, result)
            return result
        except Exception as exc:
            db.rollback()
            interview = db.get(InterviewSession, session_uuid)
            if interview:
                interview.status = "failed"
                db.commit()
            mark_failed(db, job_uuid, exc)
            raise


@celery_app.task(name="interviews.evaluate_answer")
def evaluate_answer_task(job_id: str, session_id: str, answer: str) -> dict:
    job_uuid, session_uuid = uuid.UUID(job_id), uuid.UUID(session_id)
    with SessionLocal() as db:
        job = db.get(AsyncJob, job_uuid)
        interview = db.get(InterviewSession, session_uuid)
        if not job or not interview or not interview.current_question:
            raise ValueError("任务、会话或当前问题不存在")
        try:
            mark_started(db, job)
            resume = db.get(Resume, interview.resume_id)
            jd = db.get(JobDescription, interview.jd_id)
            old_state = interview.agent_state_json or {}
            state = build_interview_graph(db).invoke(
                {
                    "phase": "answer",
                    "user_id": str(interview.user_id),
                    "profile": resume.profile_json,
                    "jd": jd.requirements_json,
                    "answered_count": interview.answered_questions,
                    "context": old_state.get("context", []),
                    "question": interview.current_question,
                    "question_type": interview.current_question_type or "question",
                    "expected_points": old_state.get("expected_points", []),
                    "answer": answer,
                }
            )
            score = state["score"]
            db.add(
                InterviewMessage(
                    session_id=interview.id,
                    sequence_no=next_sequence(db, interview.id),
                    role="candidate",
                    message_type="answer",
                    content=answer,
                    score_json=score,
                )
            )
            interview.answered_questions += 1
            job.progress = 70
            db.flush()

            if interview.answered_questions >= interview.max_questions:
                score_items = [
                    message.score_json
                    for message in db.scalars(
                        select(InterviewMessage).where(
                            InterviewMessage.session_id == interview.id,
                            InterviewMessage.message_type == "answer",
                        )
                    )
                    if message.score_json
                ]
                report_data = build_report(score_items, interview.match_result_json)
                report_dir = settings.report_dir / str(interview.user_id)
                report_dir.mkdir(parents=True, exist_ok=True)
                report_path = report_dir / f"{interview.id}.json"
                report_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
                db.add(
                    InterviewReport(
                        session_id=interview.id,
                        overall_score=report_data["overall_score"],
                        report_json=report_data,
                        report_path=str(report_path),
                    )
                )
                interview.status = "completed"
                interview.current_question = None
                interview.current_question_type = None
                result = {"session_id": str(interview.id), "completed": True, "report": report_data}
            else:
                interview.current_question = state["next_question"]
                interview.current_question_type = state.get("question_type", "question")
                interview.agent_state_json = {
                    "context": state.get("context", old_state.get("context", [])),
                    "expected_points": state.get("expected_points", old_state.get("expected_points", [])),
                    "source_chunk_ids": state.get("source_chunk_ids", []),
                }
                interview.status = "active"
                db.add(
                    InterviewMessage(
                        session_id=interview.id,
                        sequence_no=next_sequence(db, interview.id),
                        role="interviewer",
                        message_type=interview.current_question_type,
                        content=interview.current_question,
                        meta_json={"based_on_score": score},
                    )
                )
                result = {
                    "session_id": str(interview.id),
                    "completed": False,
                    "score": score,
                    "next_question": interview.current_question,
                }
            db.commit()
            mark_success(db, job, result)
            return result
        except Exception as exc:
            db.rollback()
            interview = db.get(InterviewSession, session_uuid)
            if interview:
                interview.status = "active"
                db.commit()
            mark_failed(db, job_uuid, exc)
            raise
