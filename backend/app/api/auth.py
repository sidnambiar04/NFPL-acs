from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.models.organization import Branch, Client
from app.schemas import LoginRequest, TokenResponse, UserOut
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.id == payload.username) | (User.email == payload.username)
    ).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if user.status == "INACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    """Used for simulator persona switching and user lists"""
    return db.query(User).order_by(User.id.asc()).all()

@router.get("/branches")
def list_branches(db: Session = Depends(get_db)):
    branches = db.query(Branch).all()
    return [{"id": b.id, "code": b.code, "name": b.name, "city": b.city} for b in branches]

@router.get("/clients")
def list_clients(db: Session = Depends(get_db)):
    clients = db.query(Client).all()
    return [{"id": c.id, "code": c.code, "name": c.name} for c in clients]
