from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.access_decision import AccessDecision
from app.models.audit_event import AuditEvent
from app.services.audit_service import who_could_act_at_timestamp

router = APIRouter(prefix="/audit", tags=["Audit & Governance"])

@router.get("/decisions")
def list_access_decisions(
    actor_id: Optional[str] = None,
    job_id: Optional[str] = None,
    allowed: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(AccessDecision)
    if actor_id:
        query = query.filter(AccessDecision.actor_id == actor_id)
    if job_id:
        query = query.filter(AccessDecision.job_id == job_id)
    if allowed is not None:
        query = query.filter(AccessDecision.allowed == allowed)

    return query.order_by(AccessDecision.timestamp.desc()).limit(limit).all()

@router.get("/events")
def list_audit_events(
    event_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(AuditEvent)
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    if entity_id:
        query = query.filter(AuditEvent.entity_id == entity_id)

    return query.order_by(AuditEvent.timestamp.desc()).limit(limit).all()

@router.get("/who-could-act")
def who_could_act_query(
    job_id: str,
    action: str = Query("check_job"),
    target_time: str = Query(..., description="ISO 8601 timestamp e.g. 2026-10-03T12:00:00Z"),
    db: Session = Depends(get_db)
):
    """
    Answers Question 11: 'Who could have changed this job on the 3rd?'
    Evaluates historical permissions active at the exact point in time.
    """
    try:
        dt = datetime.fromisoformat(target_time.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timestamp format. Use ISO format (e.g., 2026-10-03T12:00:00Z)"
        )

    try:
        report = who_could_act_at_timestamp(db, job_id, action, dt)
        return report
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))
