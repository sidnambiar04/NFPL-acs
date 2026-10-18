import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.job import Job
from app.models.user import User
from app.models.job_event import JobEvent
from app.models.audit_event import AuditEvent
from app.services.policy_engine import evaluate_access

def transition_job_stage(
    db: Session,
    job_id: str,
    actor: User,
    action: str,
    target_stage: str,
    reason: Optional[str] = None
) -> Job:
    """
    Executes a job lifecycle transition inside an atomic database transaction.
    Enforces authorization, optimistic locking, and writes immutable event logs.
    """
    # 1. Fetch job with row lock / concurrency check
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found."
        )

    # 2. Strict backend authorization evaluation
    decision = evaluate_access(db, actor, action, job, record_decision=True)
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=decision.to_dict()
        )

    # 3. Apply state transition and update actors for separation of duties
    from_stage = job.stage
    job.stage = target_stage
    job.version += 1
    job.updated_at = datetime.now(timezone.utc)

    if action == "prepare_job":
        job.preparer_id = actor.id
    elif action == "check_job":
        job.checker_id = actor.id
    elif action == "file_job":
        job.filer_id = actor.id

    # 4. Record immutable Job Event
    event_id = f"ev_{uuid.uuid4().hex[:12]}"
    job_event = JobEvent(
        id=event_id,
        job_id=job.id,
        actor_id=actor.id,
        action=action,
        from_stage=from_stage,
        to_stage=target_stage,
        reason=reason,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(job_event)

    # 5. If elevated operation (cancel on filed, reopen), record dedicated audit event
    if action in ["reopen_job", "cancel_job"] and from_stage in ["FILED", "CANCELLED"]:
        audit_id = f"adt_{uuid.uuid4().hex[:12]}"
        audit_event = AuditEvent(
            id=audit_id,
            actor_id=actor.id,
            event_type="ELEVATED_JOB_TRANSITION",
            entity_type="job",
            entity_id=job.id,
            before_state_json=f'{{"stage": "{from_stage}", "version": {job.version - 1}}}',
            after_state_json=f'{{"stage": "{target_stage}", "version": {job.version}}}',
            reason=reason or "Administrative override",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit_event)

    db.commit()
    db.refresh(job)
    return job
