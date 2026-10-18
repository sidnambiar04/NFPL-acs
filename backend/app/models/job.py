from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(50), primary_key=True)  # e.g. "job_1001"
    job_number = Column(String(50), unique=True, nullable=False, index=True)
    
    client_id = Column(String(50), ForeignKey("clients.id"), nullable=False, index=True)
    branch_id = Column(String(50), ForeignKey("branches.id"), nullable=False, index=True)
    
    # IMPORT, EXPORT
    direction = Column(String(20), nullable=False)
    
    # AIR, OCEAN_FCL, OCEAN_LCL
    mode = Column(String(20), nullable=False)
    
    # CONFIRMED, PREPARED, CHECKED, FILED, CANCELLED, REOPENED
    stage = Column(String(20), nullable=False, default="CONFIRMED", index=True)
    
    # Separation of duties tracking
    preparer_id = Column(String(50), ForeignKey("users.id"), nullable=True)
    checker_id = Column(String(50), ForeignKey("users.id"), nullable=True)
    filer_id = Column(String(50), ForeignKey("users.id"), nullable=True)
    
    # Optimistic locking version
    version = Column(Integer, nullable=False, default=1)
    
    description = Column(String(255), nullable=True)
    customs_entry_number = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    client = relationship("Client", foreign_keys=[client_id])
    branch = relationship("Branch", foreign_keys=[branch_id])
    preparer = relationship("User", foreign_keys=[preparer_id])
    checker = relationship("User", foreign_keys=[checker_id])
    filer = relationship("User", foreign_keys=[filer_id])
    events = relationship("JobEvent", back_populates="job", order_by="JobEvent.timestamp.desc()")

# Composite indexes for 200,000 scale fast querying
Index("ix_jobs_client_branch_stage", Job.client_id, Job.branch_id, Job.stage)
Index("ix_jobs_direction_mode_stage", Job.direction, Job.mode, Job.stage)
Index("ix_jobs_stage_created", Job.stage, Job.created_at)
