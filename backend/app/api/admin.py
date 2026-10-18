import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.role import Role, Permission, role_permissions
from app.models.role_assignment import RoleAssignment
from app.models.delegation import Delegation
from app.models.audit_event import AuditEvent
from app.schemas import RoleAssignmentCreate, RoleAssignmentOut, DelegationCreate, DelegationOut
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/admin", tags=["Administration"])

class NewRoleCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    permission_ids: List[str]

@router.get("/assignments", response_model=List[RoleAssignmentOut])
def list_assignments(user_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(RoleAssignment)
    if user_id:
        query = query.filter(RoleAssignment.user_id == user_id)
    return query.order_by(RoleAssignment.created_at.desc()).all()

@router.post("/assignments", response_model=RoleAssignmentOut)
def create_role_assignment(
    payload: RoleAssignmentCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Assigns a scoped role to a user.
    Enforces Anti-Self-Escalation: Admin cannot assign new roles to themselves directly!
    """
    if payload.user_id == current_user.id:
        # Record security violation in audit log
        audit_id = f"adt_{uuid.uuid4().hex[:12]}"
        audit_event = AuditEvent(
            id=audit_id,
            actor_id=current_user.id,
            event_type="SELF_ESCALATION_ATTEMPT_BLOCKED",
            entity_type="user",
            entity_id=current_user.id,
            before_state_json=None,
            after_state_json=f'{{"attempted_role": "{payload.role_id}"}}',
            reason="Violation of dual-control anti-self-escalation policy.",
            timestamp=datetime.now(timezone.utc)
        )
        db.add(audit_event)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anti-self-escalation policy violation: Administrators cannot assign or elevate roles for themselves."
        )

    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    asgn_id = f"asgn_{uuid.uuid4().hex[:10]}"
    assignment = RoleAssignment(
        id=asgn_id,
        user_id=payload.user_id,
        role_id=payload.role_id,
        client_id=payload.client_id,
        branch_id=payload.branch_id,
        direction=payload.direction,
        mode=payload.mode,
        valid_from=datetime.now(timezone.utc),
        valid_until=payload.valid_until,
        status="ACTIVE",
        granted_by=current_user.id,
        created_at=datetime.now(timezone.utc)
    )
    db.add(assignment)

    # Audit Trail
    audit_id = f"adt_{uuid.uuid4().hex[:12]}"
    audit_event = AuditEvent(
        id=audit_id,
        actor_id=current_user.id,
        event_type="ROLE_ASSIGNED",
        entity_type="role_assignment",
        entity_id=asgn_id,
        after_state_json=json.dumps({
            "user_id": payload.user_id,
            "role_id": payload.role_id,
            "client_id": payload.client_id,
            "branch_id": payload.branch_id,
            "direction": payload.direction,
            "mode": payload.mode
        }),
        reason="Administrative grant",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_event)
    db.commit()
    db.refresh(assignment)
    return assignment

@router.patch("/assignments/{id}/revoke", response_model=RoleAssignmentOut)
def revoke_role_assignment(
    id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    assignment = db.query(RoleAssignment).filter(RoleAssignment.id == id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    assignment.status = "REVOKED"
    assignment.valid_until = datetime.now(timezone.utc)

    audit_id = f"adt_{uuid.uuid4().hex[:12]}"
    audit_event = AuditEvent(
        id=audit_id,
        actor_id=current_user.id,
        event_type="ROLE_REVOKED",
        entity_type="role_assignment",
        entity_id=id,
        after_state_json='{"status": "REVOKED"}',
        reason="Administrative revocation",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_event)
    db.commit()
    db.refresh(assignment)
    return assignment

@router.get("/delegations", response_model=List[DelegationOut])
def list_delegations(db: Session = Depends(get_db)):
    return db.query(Delegation).order_by(Delegation.created_at.desc()).all()

@router.post("/delegations", response_model=DelegationOut)
def create_delegation(
    payload: DelegationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates an active delegation from current user (or absent user) to a colleague.
    """
    if payload.delegate_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delegate to yourself.")

    delegate = db.query(User).filter(User.id == payload.delegate_id).first()
    if not delegate or delegate.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Delegate must be an active user.")

    del_id = f"del_{uuid.uuid4().hex[:10]}"
    delegation = Delegation(
        id=del_id,
        delegator_id=current_user.id,
        delegate_id=payload.delegate_id,
        valid_from=datetime.now(timezone.utc),
        valid_until=payload.valid_until,
        status="ACTIVE",
        reason=payload.reason,
        created_at=datetime.now(timezone.utc)
    )
    db.add(delegation)

    # Automatically set delegator status to ABSENT
    current_user.status = "ABSENT"

    audit_id = f"adt_{uuid.uuid4().hex[:12]}"
    audit_event = AuditEvent(
        id=audit_id,
        actor_id=current_user.id,
        event_type="DELEGATION_CREATED",
        entity_type="delegation",
        entity_id=del_id,
        after_state_json=json.dumps({
            "delegator_id": current_user.id,
            "delegate_id": payload.delegate_id,
            "valid_until": payload.valid_until.isoformat(),
            "reason": payload.reason
        }),
        reason=payload.reason,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_event)
    db.commit()
    db.refresh(delegation)
    return delegation

@router.get("/roles")
def list_roles(db: Session = Depends(get_db)):
    roles = db.query(Role).all()
    result = []
    for r in roles:
        result.append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "is_system": r.is_system,
            "permissions": [p.id for p in r.permissions]
        })
    return result

@router.get("/permissions")
def list_permissions(db: Session = Depends(get_db)):
    perms = db.query(Permission).all()
    return [{"id": p.id, "name": p.name, "description": p.description} for p in perms]

@router.post("/roles")
def create_custom_role(
    payload: NewRoleCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Answers Question 12: How a new kind of role can be introduced while engineering is busy.
    Admins can define new roles and attach permissions entirely via database config.
    """
    existing = db.query(Role).filter(Role.id == payload.id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Role '{payload.id}' already exists.")

    new_role = Role(
        id=payload.id,
        name=payload.name,
        description=payload.description,
        is_system=False,
        created_at=datetime.now(timezone.utc)
    )

    for perm_id in payload.permission_ids:
        p = db.query(Permission).filter(Permission.id == perm_id).first()
        if p:
            new_role.permissions.append(p)

    db.add(new_role)

    # Audit event
    audit_id = f"adt_{uuid.uuid4().hex[:12]}"
    audit_event = AuditEvent(
        id=audit_id,
        actor_id=current_user.id,
        event_type="CUSTOM_ROLE_CREATED",
        entity_type="role",
        entity_id=payload.id,
        after_state_json=json.dumps({"name": payload.name, "permissions": payload.permission_ids}),
        reason="Dynamic role configuration",
        timestamp=datetime.now(timezone.utc)
    )
    db.add(audit_event)
    db.commit()
    return {"message": f"Role '{payload.id}' created successfully with {len(new_role.permissions)} permissions."}
