import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AsyncJob, JobDescription, Resume, User
from app.schemas import JDRead, ResumeRead
from app.services.file_parser import SUPPORTED_SUFFIXES
from app.tasks.jobs import parse_jd_task, parse_resume_task


router = APIRouter()
settings = get_settings()


def save_upload(file: UploadFile, user_id: uuid.UUID) -> Path:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(status_code=415, detail=f"仅支持：{', '.join(sorted(SUPPORTED_SUFFIXES))}")
    user_dir = settings.upload_dir / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    destination = user_dir / f"{uuid.uuid4()}{suffix}"
    total = 0
    with destination.open("wb") as output:
        while chunk := file.file.read(1024 * 1024):
            total += len(chunk)
            if total > settings.max_upload_mb * 1024 * 1024:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail=f"文件不能超过 {settings.max_upload_mb} MB")
            output.write(chunk)
    return destination


@router.post("/resumes", status_code=status.HTTP_202_ACCEPTED)
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    path = save_upload(file, current_user.id)
    resume = Resume(
        user_id=current_user.id,
        original_name=file.filename or path.name,
        file_path=str(path),
    )
    job = AsyncJob(user_id=current_user.id, job_type="parse_resume")
    db.add_all([resume, job])
    db.commit()
    task = parse_resume_task.delay(str(job.id), str(resume.id))
    job.celery_task_id = task.id
    db.commit()
    return {"resume_id": resume.id, "job_id": job.id, "status": "pending"}


@router.get("/resumes", response_model=list[ResumeRead])
def list_resumes(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Resume]:
    return list(db.scalars(select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.created_at.desc())))


@router.post("/job-descriptions", status_code=status.HTTP_202_ACCEPTED)
def create_jd(
    title: str = Form(...),
    text: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    path = save_upload(file, current_user.id) if file else None
    if not path and not text.strip():
        raise HTTPException(status_code=422, detail="请上传 JD 文件或填写 JD 文本")
    jd = JobDescription(
        user_id=current_user.id,
        title=title,
        original_name=file.filename if file else None,
        file_path=str(path) if path else None,
        raw_text=text.strip(),
    )
    job = AsyncJob(user_id=current_user.id, job_type="parse_jd")
    db.add_all([jd, job])
    db.commit()
    task = parse_jd_task.delay(str(job.id), str(jd.id))
    job.celery_task_id = task.id
    db.commit()
    return {"jd_id": jd.id, "job_id": job.id, "status": "pending"}


@router.get("/job-descriptions", response_model=list[JDRead])
def list_jds(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[JobDescription]:
    return list(
        db.scalars(
            select(JobDescription)
            .where(JobDescription.user_id == current_user.id)
            .order_by(JobDescription.created_at.desc())
        )
    )
