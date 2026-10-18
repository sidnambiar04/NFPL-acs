from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.work_queue import get_user_work_queue

router = APIRouter(prefix="/me", tags=["Work Queue"])

@router.get("/work-queue")
def my_work_queue(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Answers: 'Show a person the jobs that need them.'
    Guarantees that every returned job has a currently eligible required action
    matching the user's active scoped roles or delegations.
    """
    jobs, total = get_user_work_queue(db, current_user, limit=limit, offset=offset)
    return {
        "user_id": current_user.id,
        "user_name": current_user.name,
        "total_waiting": total,
        "jobs": jobs
    }
