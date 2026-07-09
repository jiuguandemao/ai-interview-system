import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import AsyncJob, User
from app.schemas import JobRead


router = APIRouter()


@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AsyncJob:
    job = db.get(AsyncJob, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job
