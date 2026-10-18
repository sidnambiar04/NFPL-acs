from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from datetime import datetime

# Auth Schemas
class LoginRequest(BaseModel):
    username: str  # id or email
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    user_type: str
    client_id: Optional[str] = None
    branch_id: Optional[str] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Job Schemas
class JobCreate(BaseModel):
    job_number: str
    client_id: str
    branch_id: str
    direction: str  # IMPORT, EXPORT
    mode: str       # AIR, OCEAN_FCL, OCEAN_LCL
    description: Optional[str] = None
    customs_entry_number: Optional[str] = None

class JobTransitionRequest(BaseModel):
    reason: Optional[str] = None

class JobOut(BaseModel):
    id: str
    job_number: str
    client_id: str
    branch_id: str
    direction: str
    mode: str
    stage: str
    preparer_id: Optional[str] = None
    checker_id: Optional[str] = None
    filer_id: Optional[str] = None
    version: int
    description: Optional[str] = None
    customs_entry_number: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobListResponse(BaseModel):
    total: int
    items: List[JobOut]

# Access Schemas
class AuthorizeRequest(BaseModel):
    action: str
    job_id: Optional[str] = None
    user_id: Optional[str] = None

class CompareRequest(BaseModel):
    user_a_id: str
    user_b_id: str
    job_id: str
    action: str

# Admin Schemas
class RoleAssignmentCreate(BaseModel):
    user_id: str
    role_id: str
    client_id: str = "*"
    branch_id: str = "*"
    direction: str = "*"
    mode: str = "*"
    valid_until: Optional[datetime] = None

class RoleAssignmentOut(BaseModel):
    id: str
    user_id: str
    role_id: str
    client_id: str
    branch_id: str
    direction: str
    mode: str
    valid_from: datetime
    valid_until: Optional[datetime] = None
    status: str
    granted_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DelegationCreate(BaseModel):
    delegate_id: str
    valid_until: datetime
    reason: str

class DelegationOut(BaseModel):
    id: str
    delegator_id: str
    delegate_id: str
    valid_from: datetime
    valid_until: datetime
    status: str
    reason: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
