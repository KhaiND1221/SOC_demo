from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import get_db
from app.logging_config import auth_logger, log_event
from app.models import Session as SessionModel
from app.models import User
from app.request_context import session_id_var, user_id_var


def get_current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    raw_session_id = request.cookies.get(settings.session_cookie_name)

    if not raw_session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        session_uuid = UUID(raw_session_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    session_obj = db.get(SessionModel, session_uuid)

    if session_obj is None or session_obj.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    now = datetime.now(timezone.utc)
    if session_obj.expires_at <= now:
        # Lazy expiry: detected and logged the moment an expired session
        # is actually used, rather than via a background sweep.
        session_obj.revoked_at = now
        db.commit()

        log_event(
            auth_logger,
            event="SESSION_EXPIRED",
            level="info",
            result="fail",
            message="Session expired",
            session_id=str(session_obj.id),
            user_id=str(session_obj.user_id),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    user = db.get(User, session_obj.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    user_id_var.set(str(user.id))
    session_id_var.set(str(session_obj.id))

    return user
