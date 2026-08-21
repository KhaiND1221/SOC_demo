from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.logging_config import app_logger, log_event
from app.models import User
from app.schemas import UserOut, UserUpdate
from app.security import hash_password

router = APIRouter(prefix="/api/users", tags=["profile"])


@router.get("/{user_id}", response_model=UserOut)
def get_profile(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        log_event(
            app_logger,
            event="authorization_denied",
            level="warning",
            result="fail",
            message="User attempted to read another user's profile",
            resource="user",
            resource_id=str(user_id),
            owner_id=str(user_id),
            requester_id=str(current_user.id),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this profile")

    log_event(
        app_logger,
        event="profile_read",
        level="info",
        result="success",
        message="Profile read",
        user_id=str(current_user.id),
    )
    return current_user


@router.put("/{user_id}", response_model=UserOut)
def update_profile(
    user_id: UUID,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if user_id != current_user.id:
        log_event(
            app_logger,
            event="authorization_denied",
            level="warning",
            result="fail",
            message="User attempted to update another user's profile",
            resource="user",
            resource_id=str(user_id),
            owner_id=str(user_id),
            requester_id=str(current_user.id),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to modify this profile")

    changed_fields = {}

    if payload.email is not None and payload.email != current_user.email:
        changed_fields["email"] = {"old": current_user.email, "new": payload.email}
        current_user.email = payload.email

    if payload.password is not None:
        current_user.password_hash = hash_password(payload.password)
        changed_fields["password"] = {"old": "***", "new": "***"}

    db.commit()
    db.refresh(current_user)

    log_event(
        app_logger,
        event="profile_update",
        level="info",
        result="success",
        message="Profile updated",
        user_id=str(current_user.id),
        changed_fields=changed_fields,
    )

    return current_user
