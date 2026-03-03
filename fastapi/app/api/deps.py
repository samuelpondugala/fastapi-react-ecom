from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.session import delete_session, get_user_id_from_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


DbSession = Annotated[Session, Depends(get_db)]
TokenDep = Annotated[str | None, Depends(oauth2_scheme)]


def _load_active_user(db: Session, user_id: int | None) -> User | None:
    if user_id is None:
        return None
    return db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))


def get_current_user(db: DbSession, request: Request, token: TokenDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if token:
        try:
            payload = decode_access_token(token)
        except ValueError:
            payload = {}

        subject = payload.get("sub")
        if subject:
            try:
                user_id = int(subject)
            except ValueError:
                user_id = None
            user = _load_active_user(db, user_id)
            if user:
                return user

    settings = get_settings()
    session_id = request.cookies.get(settings.SESSION_COOKIE_NAME)
    user_id_from_session = get_user_id_from_session(session_id)
    user = _load_active_user(db, user_id_from_session)
    if user:
        return user

    if session_id:
        delete_session(session_id)

    raise credentials_exception


def get_admin_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def get_staff_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role not in {"admin", "vendor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    return current_user
