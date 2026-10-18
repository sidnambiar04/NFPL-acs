from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Text, Index
from app.core.database import Base

class AccessDecision(Base):
    __tablename__ = "access_decisions"

    id = Column(String(50), primary_key=True)  # e.g. "dec_1001"
    actor_id = Column(String(50), nullable=False, index=True)
    job_id = Column(String(50), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    
    allowed = Column(Boolean, nullable=False)
    reason_code = Column(String(50), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    
    matched_grants_json = Column(Text, nullable=True)
    policy_version = Column(String(20), nullable=False)
    
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

Index("ix_access_decisions_actor_action", AccessDecision.actor_id, AccessDecision.action, AccessDecision.timestamp)
Index("ix_access_decisions_job_time", AccessDecision.job_id, AccessDecision.timestamp)
