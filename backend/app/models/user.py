from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)  # e.g. "usr_asha", "usr_ravi", "usr_admin"
    email = Column(String(120), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Types: STAFF, CLIENT, ADMIN, SERVICE
    user_type = Column(String(20), nullable=False, default="STAFF")
    
    # For CLIENT users, strictly scoped to their company
    client_id = Column(String(50), ForeignKey("clients.id"), nullable=True)
    
    # Home branch for staff
    branch_id = Column(String(50), ForeignKey("branches.id"), nullable=True)
    
    # Status: ACTIVE, INACTIVE, ABSENT
    status = Column(String(20), nullable=False, default="ACTIVE")
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    assignments = relationship("RoleAssignment", back_populates="user", foreign_keys="RoleAssignment.user_id")
    delegations_given = relationship("Delegation", back_populates="delegator", foreign_keys="Delegation.delegator_id")
    delegations_received = relationship("Delegation", back_populates="delegate", foreign_keys="Delegation.delegate_id")

Index("ix_users_status_type", User.status, User.user_type)
