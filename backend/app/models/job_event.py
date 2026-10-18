from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class JobEvent(Base):
    __tablename__ = "job_events"

    id = Column(String(50), primary_key=True)  # e.g. "ev_1001"
    job_id = Column(String(50), ForeignKey("jobs.id"), nullable=False, index=True)
    actor_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    
    action = Column(String(50), nullable=False)  # "create_job", "prepare_job", "check_job", "file_job", "cancel_job", "reopen_job"
    from_stage = Column(String(20), nullable=True)
    to_stage = Column(String(20), nullable=False)
    
    reason = Column(String(255), nullable=True)
    metadata_json = Column(Text, nullable=True)  # Stores JSON payload of actor context, delegation ID, etc.
    
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    job = relationship("Job", back_populates="events")
    actor = relationship("User", foreign_keys=[actor_id])

Index("ix_job_events_job_time", JobEvent.job_id, JobEvent.timestamp)
Index("ix_job_events_actor_time", JobEvent.actor_id, JobEvent.timestamp)
