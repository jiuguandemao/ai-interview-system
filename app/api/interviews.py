import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import (
    AsyncJob, InterviewMessage, InterviewReport, InterviewSession, JobDescription, Resume, User,
)
from app.schemas import AnswerCreate, InterviewCreate, InterviewRead, MessageRead, ReportRead
from app.tasks.jobs import evaluate_answer_task, prepare_interview_task


router = APIRouter()


def owned_session(db: Session, session_id: uuid.UUID, user_id: uuid.UUID) -> InterviewSession:
    interview = db.get(InterviewSession, session_id)
    if not interview or interview.user_id != user_id:
        raise HTTPException(status_code=404, detail="面试会话不存在")
    return interview


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_interview(
    payload: InterviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    resume = db.get(Resume, payload.resume_id)
    jd = db.get(JobDescription, payload.jd_id)
    if not resume or resume.user_id != current_user.id or resume.status != "ready":
        raise HTTPException(status_code=409, detail="简历不存在、未解析完成或不属于当前用户")
    if not jd or jd.user_id != current_user.id or jd.status != "ready":
        raise HTTPException(status_code=409, detail="JD 不存在、未解析完成或不属于当前用户")
    interview = InterviewSession(
        user_id=current_user.id,
        resume_id=resume.id,
        jd_id=jd.id,
        max_questions=payload.max_questions,
    )
    job = AsyncJob(user_id=current_user.id, job_type="prepare_interview")
    db.add_all([interview, job])
    db.commit()
    task = prepare_interview_task.delay(str(job.id), str(interview.id))
    job.celery_task_id = task.id
    db.commit()
    return {"session_id": interview.id, "job_id": job.id, "status": "preparing"}


@router.get("/{session_id}", response_model=InterviewRead)
def get_interview(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewSession:
    return owned_session(db, session_id, current_user.id)


@router.get("/{session_id}/messages", response_model=list[MessageRead])
def get_messages(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InterviewMessage]:
    owned_session(db, session_id, current_user.id)
    return list(
        db.scalars(
            select(InterviewMessage)
            .where(InterviewMessage.session_id == session_id)
            .order_by(InterviewMessage.sequence_no)
        )
    )


@router.post("/{session_id}/answers", status_code=status.HTTP_202_ACCEPTED)
def submit_answer(
    session_id: uuid.UUID,
    payload: AnswerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    interview = owned_session(db, session_id, current_user.id)
    if interview.status != "active" or not interview.current_question:
        raise HTTPException(status_code=409, detail="当前会话不能提交回答，可能仍在处理上一轮")
    interview.status = "processing"
    job = AsyncJob(user_id=current_user.id, job_type="evaluate_answer")
    db.add(job)
    db.commit()
    task = evaluate_answer_task.delay(str(job.id), str(interview.id), payload.answer)
    job.celery_task_id = task.id
    db.commit()
    return {"job_id": job.id, "session_id": interview.id, "status": "processing"}


@router.get("/{session_id}/report", response_model=ReportRead)
def get_report(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterviewReport:
    owned_session(db, session_id, current_user.id)
    report = db.scalar(select(InterviewReport).where(InterviewReport.session_id == session_id))
    if not report:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    return report
