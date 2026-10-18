import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.core.config import settings
from app.models.user import User
from app.models.job import Job
from app.models.role import Role, Permission
from app.models.role_assignment import RoleAssignment
from app.models.delegation import Delegation
from app.models.access_decision import AccessDecision

# Standard action to required atomic permission mapping
ACTION_PERMISSION_MAP = {
    "view": "job:view",
    "prepare_job": "job:prepare",
    "check_job": "job:check",
    "file_job": "job:file",
    "cancel_job": "job:cancel",
    "reopen_job": "job:reopen",
    "edit_filed_job": "job:edit_filed",
    "manage_roles": "admin:manage_roles",
    "create_delegation": "admin:create_delegation",
    "break_glass_repair": "admin:break_glass_repair"
}

# Stages required for sequential workflow actions
STAGE_ACTION_REQUIREMENTS = {
    "prepare_job": ["CONFIRMED"],
    "check_job": ["PREPARED"],
    "file_job": ["CHECKED"],
    "cancel_job": ["CONFIRMED", "PREPARED", "CHECKED", "FILED"],
    "reopen_job": ["FILED", "CANCELLED"]
}

class DecisionResult:
    def __init__(
        self,
        allowed: bool,
        action: str,
        reason_code: str,
        reason: str,
        actor_id: str,
        job_id: Optional[str] = None,
        matched_grants: Optional[List[Dict[str, Any]]] = None,
        missing_requirements: Optional[List[str]] = None,
        policy_version: str = settings.POLICY_VERSION
    ):
        self.allowed = allowed
        self.action = action
        self.reason_code = reason_code
        self.reason = reason
        self.actor_id = actor_id
        self.job_id = job_id
        self.matched_grants = matched_grants or []
        self.missing_requirements = missing_requirements or []
        self.policy_version = policy_version
        self.evaluated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "actor_id": self.actor_id,
            "job_id": self.job_id,
            "matched_grants": self.matched_grants,
            "missing_requirements": self.missing_requirements,
            "policy_version": self.policy_version,
            "evaluated_at": self.evaluated_at
        }

def evaluate_access(
    db: Session,
    actor: User,
    action: str,
    job: Optional[Job] = None,
    evaluation_time: Optional[datetime] = None,
    record_decision: bool = False
) -> DecisionResult:
    """
    Central Policy Engine evaluating access requests based on:
    1. Actor account status & user type
    2. Tenant isolation (for Client users)
    3. Workflow stage preconditions
    4. Separation of Duties (4-Eyes rule for Maker/Checker)
    5. Scoped Role Grants + Active Time-bounded Delegations
    6. Special elevated permissions (Reopen, Cancel Filed, Admin)
    """
    eval_time = evaluation_time or datetime.now(timezone.utc)
    # Ensure timezone naive vs aware comparison is safe
    if eval_time.tzinfo is not None:
        eval_time = eval_time.replace(tzinfo=None)

    actor_id = actor.id
    job_id = job.id if job else None

    try:
        # Layer 1: Account Status Check
        if actor.status == "INACTIVE":
            return _deny(db, actor_id, job_id, action, "ACCOUNT_INACTIVE",
                         f"User '{actor.name}' ({actor_id}) account is INACTIVE.",
                         ["ACTIVE_ACCOUNT_STATUS"], record_decision)
        
        if actor.status == "ABSENT":
            # An absent user cannot act themselves; their delegate must act on their behalf
            return _deny(db, actor_id, job_id, action, "ACCOUNT_ABSENT",
                         f"User '{actor.name}' ({actor_id}) is marked ABSENT. Direct actions must be performed by an assigned delegate.",
                         ["ACTIVE_NON_ABSENT_STATUS"], record_decision)

        # Layer 2: Client Tenancy Check
        if actor.user_type == "CLIENT":
            if action != "view":
                return _deny(db, actor_id, job_id, action, "CLIENT_ACTION_RESTRICTED",
                             "Client users have read-only visibility into their shipments.",
                             ["INTERNAL_STAFF_OR_ADMIN_ROLE"], record_decision)
            if job and actor.client_id and job.client_id != actor.client_id:
                return _deny(db, actor_id, job_id, action, "CLIENT_ISOLATION_VIOLATION",
                             f"Cross-client access denied: Job belongs to '{job.client_id}' but actor is assigned to '{actor.client_id}'.",
                             ["CLIENT_OWNERSHIP_MATCH"], record_decision)

        # Layer 3: Service Identity / Parser Boundaries
        if actor.user_type == "SERVICE":
            # Parser service is restricted to creating jobs and updating draft/confirmed
            allowed_service_actions = ["create_job", "prepare_job", "view"]
            if action not in allowed_service_actions:
                return _deny(db, actor_id, job_id, action, "SERVICE_ACCOUNT_RESTRICTED",
                             f"Service identity '{actor_id}' is restricted from performing '{action}'.",
                             ["HUMAN_STAFF_INTERACTION"], record_decision)

        # Layer 4: Job-Specific Workflow & State Validations
        if job:
            # Check Filed Job Immutability
            if job.stage == "FILED" and action in ["prepare_job", "check_job", "edit_filed_job"]:
                return _deny(db, actor_id, job_id, action, "JOB_LOCKED_FILED",
                             f"Job {job.job_number} is FILED and locked against ordinary modifications.",
                             ["WORKFLOW_REOPEN_OR_AMENDMENT_PERMISSION"], record_decision)

            # Check Cancelled Job Immutability
            if job.stage == "CANCELLED" and action != "reopen_job" and action != "view":
                return _deny(db, actor_id, job_id, action, "JOB_CANCELLED_LOCKED",
                             f"Job {job.job_number} is CANCELLED. Only reopen_job or view is permitted.",
                             ["JOB_NOT_CANCELLED"], record_decision)

            # Stage Preconditions
            if action in STAGE_ACTION_REQUIREMENTS:
                required_stages = STAGE_ACTION_REQUIREMENTS[action]
                if job.stage not in required_stages:
                    return _deny(db, actor_id, job_id, action, "INVALID_STAGE",
                                 f"Action '{action}' requires stage {required_stages}, but current stage is '{job.stage}'.",
                                 [f"STAGE_IN_{required_stages}"], record_decision)

            # Layer 5: Separation of Duties (4-Eyes Principle)
            if action == "check_job":
                if job.preparer_id and job.preparer_id == actor.id:
                    return _deny(db, actor_id, job_id, action, "SAME_PERSON_MAKER_CHECKER",
                                 f"Separation of Duties violation: Actor '{actor.name}' prepared this job and cannot approve/check their own work.",
                                 ["DIFFERENT_ACTOR_THAN_PREPARER"], record_decision)

        # Layer 6: Required Permission Resolution
        required_permission = ACTION_PERMISSION_MAP.get(action)
        if not required_permission:
            return _deny(db, actor_id, job_id, action, "UNKNOWN_ACTION",
                         f"Action '{action}' is not recognized by the policy engine.",
                         ["VALID_ACTION_DEFINITION"], record_decision)

        # Layer 7: Gather Active Grants (Direct + Delegated)
        candidate_grants = []

        # 7a. Direct role assignments
        direct_assignments = db.query(RoleAssignment).filter(
            RoleAssignment.user_id == actor.id,
            RoleAssignment.status == "ACTIVE",
            RoleAssignment.valid_from <= eval_time,
            or_(RoleAssignment.valid_until.is_(None), RoleAssignment.valid_until >= eval_time)
        ).all()

        for asgn in direct_assignments:
            candidate_grants.append({
                "assignment_id": asgn.id,
                "role_id": asgn.role_id,
                "client_id": asgn.client_id,
                "branch_id": asgn.branch_id,
                "direction": asgn.direction,
                "mode": asgn.mode,
                "delegated_from": None
            })

        # 7b. Delegated role assignments (Active Out-of-Office coverage)
        active_delegations = db.query(Delegation).filter(
            Delegation.delegate_id == actor.id,
            Delegation.status == "ACTIVE",
            Delegation.valid_from <= eval_time,
            Delegation.valid_until >= eval_time
        ).all()

        for delegation in active_delegations:
            delegator_assignments = db.query(RoleAssignment).filter(
                RoleAssignment.user_id == delegation.delegator_id,
                RoleAssignment.status == "ACTIVE",
                RoleAssignment.valid_from <= eval_time,
                or_(RoleAssignment.valid_until.is_(None), RoleAssignment.valid_until >= eval_time)
            ).all()

            for asgn in delegator_assignments:
                candidate_grants.append({
                    "assignment_id": asgn.id,
                    "role_id": asgn.role_id,
                    "client_id": asgn.client_id,
                    "branch_id": asgn.branch_id,
                    "direction": asgn.direction,
                    "mode": asgn.mode,
                    "delegated_from": delegation.delegator_id,
                    "delegation_reason": delegation.reason
                })

        # Layer 8: Filter by Role Permissions & 4D Scope Matching
        matched_grants = []
        near_miss_reasons = []

        for grant in candidate_grants:
            # Check if this role possesses the required permission
            role_obj = db.query(Role).filter(Role.id == grant["role_id"]).first()
            if not role_obj:
                continue

            has_permission = any(p.id == required_permission for p in role_obj.permissions)
            if not has_permission:
                continue

            # If no job is evaluated (global action), role permission match is sufficient
            if not job:
                matched_grants.append(grant)
                continue

            # 4-Dimensional Scope Matching
            match_client = (grant["client_id"] == "*" or grant["client_id"] == job.client_id)
            match_branch = (grant["branch_id"] == "*" or grant["branch_id"] == job.branch_id)
            match_direction = (grant["direction"] == "*" or grant["direction"] == job.direction)
            match_mode = (grant["mode"] == "*" or grant["mode"] == job.mode)

            if match_client and match_branch and match_direction and match_mode:
                matched_grants.append(grant)
            else:
                mismatches = []
                if not match_client:
                    mismatches.append(f"client '{grant['client_id']}' != '{job.client_id}'")
                if not match_branch:
                    mismatches.append(f"branch '{grant['branch_id']}' != '{job.branch_id}'")
                if not match_direction:
                    mismatches.append(f"direction '{grant['direction']}' != '{job.direction}'")
                if not match_mode:
                    mismatches.append(f"mode '{grant['mode']}' != '{job.mode}'")
                near_miss_reasons.append(
                    f"Role {grant['role_id']} has '{required_permission}' but scope mismatched on: " + ", ".join(mismatches)
                )

        if matched_grants:
            # Grant Allowed!
            primary_grant = matched_grants[0]
            delegation_note = f" (via active delegation from {primary_grant['delegated_from']})" if primary_grant.get("delegated_from") else ""
            reason = (
                f"Granted via role '{primary_grant['role_id']}'{delegation_note} covering scope "
                f"[client={primary_grant['client_id']}, branch={primary_grant['branch_id']}, "
                f"direction={primary_grant['direction']}, mode={primary_grant['mode']}]."
            )
            result = DecisionResult(
                allowed=True,
                action=action,
                reason_code="ALLOWED",
                reason=reason,
                actor_id=actor_id,
                job_id=job_id,
                matched_grants=matched_grants
            )
            if record_decision:
                _save_decision(db, result)
            return result

        # If we reached here, no active grant matched
        if near_miss_reasons:
            explanation = "Scope mismatch: " + " | ".join(near_miss_reasons[:2])
            return _deny(db, actor_id, job_id, action, "SCOPE_MISMATCH", explanation,
                         ["MATCHING_SCOPE_PARAMETERS"], record_decision)
        else:
            return _deny(db, actor_id, job_id, action, "ROLE_NOT_ASSIGNED",
                         f"User '{actor.name}' does not possess any active role with permission '{required_permission}'.",
                         [f"ROLE_WITH_{required_permission}"], record_decision)

    except Exception as ex:
        # Fail Closed on unexpected error or uncertain state
        return _deny(db, actor_id, job_id, action, "SYSTEM_UNSURE_FAIL_CLOSED",
                     f"System failed closed due to unexpected evaluation state: {str(ex)}",
                     ["CONTACT_COMPLIANCE_ADMIN"], record_decision)

def _deny(
    db: Session,
    actor_id: str,
    job_id: Optional[str],
    action: str,
    reason_code: str,
    reason: str,
    missing_requirements: List[str],
    record_decision: bool
) -> DecisionResult:
    result = DecisionResult(
        allowed=False,
        action=action,
        reason_code=reason_code,
        reason=reason,
        actor_id=actor_id,
        job_id=job_id,
        missing_requirements=missing_requirements
    )
    if record_decision:
        _save_decision(db, result)
    return result

def _save_decision(db: Session, decision: DecisionResult):
    import uuid
    record = AccessDecision(
        id=f"dec_{uuid.uuid4().hex[:12]}",
        actor_id=decision.actor_id,
        job_id=decision.job_id,
        action=decision.action,
        allowed=decision.allowed,
        reason_code=decision.reason_code,
        reason=decision.reason,
        matched_grants_json=json.dumps(decision.matched_grants),
        policy_version=decision.policy_version,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(record)
    db.commit()
