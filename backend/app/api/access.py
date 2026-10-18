from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.schemas import AuthorizeRequest, CompareRequest
from app.api.deps import get_current_user
from app.services.policy_engine import evaluate_access
from app.services.audit_service import compare_user_access

router = APIRouter(prefix="/access", tags=["Access & Explainability"])

@router.post("/authorize")
def authorize_action(
    payload: AuthorizeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Answers: 'May this person perform this action on this job, and why?'
    If user_id is passed, evaluates that user (useful for admins or simulator);
    otherwise evaluates the authenticated user.
    """
    target_user = current_user
    if payload.user_id and payload.user_id != current_user.id:
        target_user = db.query(User).filter(User.id == payload.user_id).first()
        if not target_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User '{payload.user_id}' not found.")

    target_job = None
    if payload.job_id:
        target_job = db.query(Job).filter(Job.id == payload.job_id).first()
        if not target_job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job '{payload.job_id}' not found.")

    decision = evaluate_access(db, target_user, payload.action, target_job, record_decision=True)
    return decision.to_dict()

@router.post("/compare")
def compare_access(
    payload: CompareRequest,
    db: Session = Depends(get_db)
):
    """
    Answers Question 10: 'Why can she do this and he can't?'
    Generates a comparative analysis between User A and User B.
    """
    try:
        comparison = compare_user_access(
            db=db,
            user_a_id=payload.user_a_id,
            user_b_id=payload.user_b_id,
            job_id=payload.job_id,
            action=payload.action
        )
        return comparison
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))
