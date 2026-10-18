import uuid
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.job import Job
from app.models.job_event import JobEvent
from app.models.user import User
from app.schemas import JobCreate, JobOut, JobListResponse, JobTransitionRequest
from app.api.deps import get_current_user
from app.services.policy_engine import evaluate_access
from app.services.workflow_service import transition_job_stage

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("", response_model=JobListResponse)
def list_jobs(
    stage: Optional[str] = None,
    client_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    direction: Optional[str] = None,
    mode: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Job)

    # Tenant isolation: Client users can ONLY ever see their company's shipments
    if current_user.user_type == "CLIENT":
        query = query.filter(Job.client_id == current_user.client_id)
    elif client_id:
        query = query.filter(Job.client_id == client_id)

    if stage:
        query = query.filter(Job.stage == stage)
    if branch_id:
        query = query.filter(Job.branch_id == branch_id)
    if direction:
        query = query.filter(Job.direction == direction)
    if mode:
        query = query.filter(Job.mode == mode)
    if search:
        query = query.filter(
            or_(
                Job.job_number.ilike(f"%{search}%"),
                Job.description.ilike(f"%{search}%"),
                Job.customs_entry_number.ilike(f"%{search}%")
            )
        )

    total = query.count()
    items = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": items}

@router.get("/{id}", response_model=JobOut)
def get_job(id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    decision = evaluate_access(db, current_user, "view", job)
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.to_dict())

    return job

@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verify user may create jobs
    if current_user.user_type not in ["STAFF", "ADMIN", "SERVICE"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clients cannot create jobs directly.")

    new_job = Job(
        id=f"job_{uuid.uuid4().hex[:10]}",
        job_number=payload.job_number,
        client_id=payload.client_id,
        branch_id=payload.branch_id,
        direction=payload.direction,
        mode=payload.mode,
        stage="CONFIRMED",
        description=payload.description,
        customs_entry_number=payload.customs_entry_number,
        version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(new_job)

    # Initial creation event
    event = JobEvent(
        id=f"ev_{uuid.uuid4().hex[:12]}",
        job_id=new_job.id,
        actor_id=current_user.id,
        action="create_job",
        from_stage=None,
        to_stage="CONFIRMED",
        reason="Initial shipment job creation",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(event)
    db.commit()
    db.refresh(new_job)
    return new_job

@router.get("/{id}/available-actions")
def get_available_actions(id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Evaluates every potential lifecycle action for this user on this job.
    Allows frontend to display contextual buttons with tooltip explanations!
    """
    job = db.query(Job).filter(Job.id == id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    actions_to_check = ["prepare_job", "check_job", "file_job", "cancel_job", "reopen_job"]
    evaluations = {}

    for action in actions_to_check:
        dec = evaluate_access(db, current_user, action, job)
        evaluations[action] = {
            "allowed": dec.allowed,
            "reason_code": dec.reason_code,
            "reason": dec.reason
        }

    return {"job_id": job.id, "stage": job.stage, "evaluations": evaluations}

@router.post("/{id}/prepare", response_model=JobOut)
def prepare_job(id: str, payload: JobTransitionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return transition_job_stage(db, id, current_user, "prepare_job", "PREPARED", payload.reason)

@router.post("/{id}/check", response_model=JobOut)
def check_job(id: str, payload: JobTransitionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return transition_job_stage(db, id, current_user, "check_job", "CHECKED", payload.reason)

@router.post("/{id}/file", response_model=JobOut)
def file_job(id: str, payload: JobTransitionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return transition_job_stage(db, id, current_user, "file_job", "FILED", payload.reason)

@router.post("/{id}/cancel", response_model=JobOut)
def cancel_job(id: str, payload: JobTransitionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not payload.reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A mandatory justification reason is required to cancel a shipment.")
    return transition_job_stage(db, id, current_user, "cancel_job", "CANCELLED", payload.reason)

@router.post("/{id}/reopen", response_model=JobOut)
def reopen_job(id: str, payload: JobTransitionRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not payload.reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A mandatory justification reason is required to reopen a closed/filed shipment.")
    return transition_job_stage(db, id, current_user, "reopen_job", "REOPENED", payload.reason)

@router.get("/{id}/history")
def get_job_history(id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    decision = evaluate_access(db, current_user, "view", job)
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=decision.to_dict())

    events = db.query(JobEvent).filter(JobEvent.job_id == id).order_by(JobEvent.timestamp.asc()).all()
    
    result = []
    for ev in events:
        actor = db.query(User).filter(User.id == ev.actor_id).first()
        result.append({
            "id": ev.id,
            "action": ev.action,
            "from_stage": ev.from_stage,
            "to_stage": ev.to_stage,
            "reason": ev.reason,
            "timestamp": ev.timestamp.isoformat(),
            "actor": {
                "id": ev.actor_id,
                "name": actor.name if actor else ev.actor_id,
                "user_type": actor.user_type if actor else "UNKNOWN"
            }
        })

    return {"job_id": job.id, "job_number": job.job_number, "timeline": result}
