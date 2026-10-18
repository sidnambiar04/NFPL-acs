from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class Delegation(Base):
    __tablename__ = "delegations"

    id = Column(String(50), primary_key=True)  # e.g. "del_1001"
    delegator_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    delegate_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    
    valid_from = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    valid_until = Column(DateTime, nullable=False)
    
    # ACTIVE, REVOKED, EXPIRED
    status = Column(String(20), nullable=False, default="ACTIVE")
    reason = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    delegator = relationship("User", foreign_keys=[delegator_id], back_populates="delegations_given")
    delegate = relationship("User", foreign_keys=[delegate_id], back_populates="delegations_received")

Index("ix_delegation_lookup", Delegation.delegate_id, Delegation.status, Delegation.valid_from, Delegation.valid_until)
