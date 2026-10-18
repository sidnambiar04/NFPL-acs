from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Index
from app.core.database import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(50), primary_key=True)  # e.g. "adt_1001"
    actor_id = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # e.g. "ROLE_ASSIGNED", "ROLE_REVOKED", "DELEGATION_CREATED", "BREAK_GLASS_REPAIR"
    entity_type = Column(String(50), nullable=False)  # "role_assignment", "delegation", "job", "user"
    entity_id = Column(String(50), nullable=False, index=True)
    
    before_state_json = Column(Text, nullable=True)
    after_state_json = Column(Text, nullable=True)
    reason = Column(String(255), nullable=True)
    
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

Index("ix_audit_events_entity", AuditEvent.entity_type, AuditEvent.entity_id, AuditEvent.timestamp)
Index("ix_audit_events_actor", AuditEvent.actor_id, AuditEvent.timestamp)
