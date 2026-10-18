from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class RoleAssignment(Base):
    __tablename__ = "role_assignments"

    id = Column(String(50), primary_key=True)  # e.g. "asgn_1001"
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(String(50), ForeignKey("roles.id"), nullable=False, index=True)
    
    # 4-dimensional scope: explicit "*" signifies wildcard (ALL)
    client_id = Column(String(50), nullable=False, default="*")
    branch_id = Column(String(50), nullable=False, default="*")
    direction = Column(String(20), nullable=False, default="*")
    mode = Column(String(20), nullable=False, default="*")
    
    valid_from = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    valid_until = Column(DateTime, nullable=True)
    
    # ACTIVE, REVOKED, EXPIRED
    status = Column(String(20), nullable=False, default="ACTIVE")
    
    granted_by = Column(String(50), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id], back_populates="assignments")
    role = relationship("Role", foreign_keys=[role_id])
    grantor = relationship("User", foreign_keys=[granted_by])

Index("ix_role_assignments_eval", RoleAssignment.user_id, RoleAssignment.status, RoleAssignment.valid_from, RoleAssignment.valid_until)
Index("ix_role_assignments_scope", RoleAssignment.client_id, RoleAssignment.branch_id, RoleAssignment.direction, RoleAssignment.mode)
