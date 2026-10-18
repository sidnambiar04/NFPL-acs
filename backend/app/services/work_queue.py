from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, not_

from app.models.job import Job
from app.models.user import User
from app.models.role import Role
from app.models.role_assignment import RoleAssignment
from app.models.delegation import Delegation
from app.services.policy_engine import evaluate_access

def get_user_work_queue(
    db: Session,
    actor: User,
    limit: int = 50,
    offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Returns jobs that currently require an action that the given actor is eligible to perform.
    Enforces the EXACT same rules as the authorization engine:
    - CONFIRMED jobs if actor has MAKER scope
    - PREPARED jobs if actor has CHECKER scope AND actor != preparer_id (Separation of Duties!)
    - CHECKED jobs if actor has FILER scope
    """
    if actor.status != "ACTIVE":
        return [], 0

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. Gather all active assignments (direct + delegated)
    active_assignments = db.query(RoleAssignment).filter(
        RoleAssignment.user_id == actor.id,
        RoleAssignment.status == "ACTIVE",
        RoleAssignment.valid_from <= now,
        or_(RoleAssignment.valid_until.is_(None), RoleAssignment.valid_until >= now)
    ).all()

    # Active delegations
    delegations = db.query(Delegation).filter(
        Delegation.delegate_id == actor.id,
        Delegation.status == "ACTIVE",
        Delegation.valid_from <= now,
        Delegation.valid_until >= now
    ).all()

    for dlg in delegations:
        dlg_assignments = db.query(RoleAssignment).filter(
            RoleAssignment.user_id == dlg.delegator_id,
            RoleAssignment.status == "ACTIVE",
            RoleAssignment.valid_from <= now,
            or_(RoleAssignment.valid_until.is_(None), RoleAssignment.valid_until >= now)
        ).all()
        active_assignments.extend(dlg_assignments)

    if not active_assignments:
        return [], 0

    # 2. Build scope filter clauses for each stage
    maker_clauses = []
    checker_clauses = []
    filer_clauses = []

    for asgn in active_assignments:
        role = db.query(Role).filter(Role.id == asgn.role_id).first()
        if not role:
            continue
        
        perms = [p.id for p in role.permissions]

        def build_scope_filter(a: RoleAssignment):
            conditions = []
            if a.client_id != "*":
                conditions.append(Job.client_id == a.client_id)
            if a.branch_id != "*":
                conditions.append(Job.branch_id == a.branch_id)
            if a.direction != "*":
                conditions.append(Job.direction == a.direction)
            if a.mode != "*":
                conditions.append(Job.mode == a.mode)
            return and_(*conditions) if conditions else True

        scope_cond = build_scope_filter(asgn)

        if "job:prepare" in perms:
            maker_clauses.append(and_(Job.stage == "CONFIRMED", scope_cond))
        
        if "job:check" in perms:
            # 4-eyes enforcement: preparer cannot be the checker!
            checker_clauses.append(
                and_(
                    Job.stage == "PREPARED",
                    or_(Job.preparer_id.is_(None), Job.preparer_id != actor.id),
                    scope_cond
                )
            )

        if "job:file" in perms:
            filer_clauses.append(and_(Job.stage == "CHECKED", scope_cond))

    all_eligibility_clauses = maker_clauses + checker_clauses + filer_clauses
    if not all_eligibility_clauses:
        return [], 0

    # Combine with OR
    combined_filter = or_(*all_eligibility_clauses)

    # 3. Query total count and paged jobs
    query = db.query(Job).filter(combined_filter)
    total_count = query.count()
    jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    # 4. Formulate response payload with verified action
    result = []
    for job in jobs:
        next_action = None
        if job.stage == "CONFIRMED":
            next_action = "prepare_job"
        elif job.stage == "PREPARED":
            next_action = "check_job"
        elif job.stage == "CHECKED":
            next_action = "file_job"

        # Double check via authorization engine to guarantee zero drift
        decision = evaluate_access(db, actor, next_action, job)

        result.append({
            "id": job.id,
            "job_number": job.job_number,
            "client_id": job.client_id,
            "branch_id": job.branch_id,
            "direction": job.direction,
            "mode": job.mode,
            "stage": job.stage,
            "preparer_id": job.preparer_id,
            "checker_id": job.checker_id,
            "created_at": job.created_at.isoformat(),
            "required_action": next_action,
            "can_act": decision.allowed,
            "action_explanation": decision.reason
        })

    return result, total_count
