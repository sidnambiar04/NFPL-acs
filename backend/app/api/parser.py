import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.job_event import JobEvent
from app.api.deps import get_current_user

router = APIRouter(prefix="/parser", tags=["Automated Parser Integration"])

class ParserJobIngest(BaseModel):
    job_number: str
    client_id: str
    branch_id: str
    direction: str
    mode: str
    description: Optional[str] = None
    customs_entry_number: Optional[str] = None
    external_manifest_hash: str  # For idempotent retries

class ParserBatchResponse(BaseModel):
    processed: int
    created: int
    skipped_duplicates: int
    errors: List[str]

@router.post("/jobs", response_model=ParserBatchResponse)
def ingest_parser_jobs(
    jobs: List[ParserJobIngest],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Answers Question 9: Dedicated overnight parser endpoint.
    - Restricted to SERVICE accounts.
    - Idempotent against duplicate retries.
    - Strictly limited to creating CONFIRMED/DRAFT jobs without approving/filing authority.
    """
    if current_user.user_type != "SERVICE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Endpoint restricted to authorized machine service identities (parsers)."
        )

    created_count = 0
    skipped_count = 0
    errors = []

    for item in jobs:
        # Check idempotency: if job with job_number already exists, skip
        existing = db.query(Job).filter(Job.job_number == item.job_number).first()
        if existing:
            skipped_count += 1
            continue

        try:
            job_id = f"job_{uuid.uuid4().hex[:10]}"
            new_job = Job(
                id=job_id,
                job_number=item.job_number,
                client_id=item.client_id,
                branch_id=item.branch_id,
                direction=item.direction,
                mode=item.mode,
                stage="CONFIRMED",
                description=item.description,
                customs_entry_number=item.customs_entry_number,
                version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(new_job)

            # Record parser creation event
            event = JobEvent(
                id=f"ev_{uuid.uuid4().hex[:12]}",
                job_id=job_id,
                actor_id=current_user.id,
                action="parser_ingest",
                from_stage=None,
                to_stage="CONFIRMED",
                reason=f"Overnight automated manifest sync (hash: {item.external_manifest_hash})",
                timestamp=datetime.now(timezone.utc)
            )
            db.add(event)
            created_count += 1
        except Exception as ex:
            errors.append(f"Failed job {item.job_number}: {str(ex)}")

    db.commit()

    return {
        "processed": len(jobs),
        "created": created_count,
        "skipped_duplicates": skipped_count,
        "errors": errors
    }
