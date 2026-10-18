from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id")
) -> User:
    """
    Resolves the current actor.
    Supports standard JWT Bearer token OR rapid persona switcher header (X-User-Id).
    """
    user_id = None
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user_id = payload["sub"]
    
    # Allow X-User-Id header if token not provided (ideal for demo persona switcher & automated test runner)
    if not user_id and x_user_id:
        user_id = x_user_id

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token or X-User-Id header."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User identity '{user_id}' does not exist."
        )

    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.user_type != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return current_user
