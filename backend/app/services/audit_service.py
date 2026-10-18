from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User
from app.models.job import Job
from app.models.job_event import JobEvent
from app.models.role_assignment import RoleAssignment
from app.models.delegation import Delegation
from app.services.policy_engine import evaluate_access

def compare_user_access(
    db: Session,
    user_a_id: str,
    user_b_id: str,
    job_id: str,
    action: str
) -> Dict[str, Any]:
    """
    Answers Question 10: 'Why can she do this and he can't?'
    Provides a deep side-by-side diagnostic diff of both actors for a given job and action.
    """
    user_a = db.query(User).filter(User.id == user_a_id).first()
    user_b = db.query(User).filter(User.id == user_b_id).first()
    job = db.query(Job).filter(Job.id == job_id).first()

    if not user_a or not user_b:
        raise ValueError("One or both users not found.")
    if not job:
        raise ValueError("Job not found.")

    decision_a = evaluate_access(db, user_a, action, job, ignore_stage=True)
    decision_b = evaluate_access(db, user_b, action, job, ignore_stage=True)

    # Analyze root cause of divergence
    divergence_summary = []
    if decision_a.allowed != decision_b.allowed:
        allowed_user = user_a.name if decision_a.allowed else user_b.name
        denied_user = user_b.name if decision_a.allowed else user_a.name
        denied_decision = decision_b if decision_a.allowed else decision_a

        divergence_summary.append(
            f"{allowed_user} is permitted because they matched an active grant, whereas {denied_user} was denied due to: {denied_decision.reason_code} ({denied_decision.reason})."
        )
    elif decision_a.allowed and decision_b.allowed:
        divergence_summary.append("Both users are authorized by role and scope to perform this action on this job.")
    else:
        divergence_summary.append("Both users are denied permission for this action on this job.")

    if job.stage != "PREPARED" and action == "check_job":
        divergence_summary.append(f"(Note: Current live job stage is '{job.stage}'; in live execution, check_job requires PREPARED stage).")
    elif job.stage != "CONFIRMED" and action == "prepare_job":
        divergence_summary.append(f"(Note: Current live job stage is '{job.stage}'; in live execution, prepare_job requires CONFIRMED stage).")

    return {
        "job_id": job.id,
        "job_number": job.job_number,
        "action": action,
        "comparison_summary": " ".join(divergence_summary),
        "user_a": {
            "id": user_a.id,
            "name": user_a.name,
            "user_type": user_a.user_type,
            "decision": decision_a.to_dict()
        },
        "user_b": {
            "id": user_b.id,
            "name": user_b.name,
            "user_type": user_b.user_type,
            "decision": decision_b.to_dict()
        }
    }

def who_could_act_at_timestamp(
    db: Session,
    job_id: str,
    action: str,
    target_time: datetime
) -> Dict[str, Any]:
    """
    Answers Question 11: 'Who could have changed this job on the 3rd?'
    Reconstructs the exact point-in-time authorization state at target_time.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError("Job not found.")

    if target_time.tzinfo is not None:
        clean_time = target_time.replace(tzinfo=None)
    else:
        clean_time = target_time

    # Find all users who were active at that timestamp
    all_users = db.query(User).all()
    eligible_users = []

    for user in all_users:
        # Evaluate access using historical point-in-time timestamp (evaluating role and scope at that date)
        decision = evaluate_access(db, user, action, job, evaluation_time=clean_time, ignore_stage=True)
        if decision.allowed:
            eligible_users.append({
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "user_type": user.user_type,
                "reason": decision.reason,
                "matched_grants": decision.matched_grants
            })

    # Also retrieve any actual events recorded around that date
    actual_events = db.query(JobEvent).filter(
        JobEvent.job_id == job_id
    ).order_by(JobEvent.timestamp.asc()).all()

    events_summary = []
    for ev in actual_events:
        events_summary.append({
            "id": ev.id,
            "actor_id": ev.actor_id,
            "action": ev.action,
            "from_stage": ev.from_stage,
            "to_stage": ev.to_stage,
            "timestamp": ev.timestamp.isoformat(),
            "reason": ev.reason
        })

    return {
        "job_id": job.id,
        "job_number": job.job_number,
        "action": action,
        "target_timestamp": target_time.isoformat(),
        "eligible_user_count": len(eligible_users),
        "eligible_users": eligible_users,
        "historical_job_events": events_summary
    }
