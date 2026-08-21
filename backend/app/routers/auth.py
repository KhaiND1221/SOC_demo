from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import get_db
from app.logging_config import app_logger, auth_logger, log_event
from app.models import LoginAttempt
from app.models import Session as SessionModel
from app.models import User
from app.request_context import source_ip_var
from app.schemas import LoginRequest, UserCreate, UserOut
from app.security import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DBSession = Depends(get_db)):
    existing = (
        db.query(User)
        .filter((User.username == payload.username) | (User.email == payload.email))
        .first()
    )

    if existing:
        log_event(
            app_logger,
            event="register",
            level="warning",
            result="fail",
            message="Registration failed: username or email already exists",
            username=payload.username,
            email=payload.email,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered")

    user = User(username=payload.username, email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        log_event(
            app_logger,
            event="register",
            level="warning",
            result="fail",
            message="Registration failed: integrity error",
            username=payload.username,
            email=payload.email,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already registered")

    db.refresh(user)

    log_event(
        app_logger,
        event="register",
        level="info",
        result="success",
        message="User registered",
        user_id=str(user.id),
        username=user.username,
    )

    return user


def _recent_failed_count(db: DBSession, *, username: str, ip: str, window_minutes: int) -> int:
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    return (
        db.query(func.count(LoginAttempt.id))
        .filter(
            LoginAttempt.success.is_(False),
            LoginAttempt.created_at >= since,
            (LoginAttempt.username == username) | (LoginAttempt.ip_address == ip),
        )
        .scalar()
        or 0
    )


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response, db: DBSession = Depends(get_db)):
    ip = source_ip_var.get() or (request.client.host if request.client else "unknown")

    fail_count = _recent_failed_count(
        db, username=payload.username, ip=ip, window_minutes=settings.rate_limit_window_minutes
    )

    if fail_count >= settings.rate_limit_max_attempts:
        log_event(
            auth_logger,
            event="LOGIN_FAIL",
            level="warning",
            result="fail",
            message="Login blocked: account temporarily locked",
            username=payload.username,
            ip_address=ip,
            reason="account_locked",
            fail_count=fail_count,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to repeated failed logins",
        )

    user = db.query(User).filter(User.username == payload.username).first()

    if user is None or not verify_password(payload.password, user.password_hash):
        reason = "user_not_found" if user is None else "bad_password"

        db.add(LoginAttempt(username=payload.username, ip_address=ip, success=False))
        db.commit()

        new_fail_count = _recent_failed_count(
            db, username=payload.username, ip=ip, window_minutes=settings.rate_limit_window_minutes
        )

        log_event(
            auth_logger,
            event="LOGIN_FAIL",
            level="warning",
            result="fail",
            message="Login failed",
            username=payload.username,
            ip_address=ip,
            reason=reason,
            fail_count=new_fail_count,
        )
        log_event(
            app_logger,
            event="login_fail",
            level="warning",
            result="fail",
            message="Login failed",
            username=payload.username,
            reason=reason,
        )

        if new_fail_count >= settings.rate_limit_max_attempts:
            log_event(
                auth_logger,
                event="ACCOUNT_LOCKED",
                level="warning",
                result="fail",
                message="Account locked after repeated failed logins",
                username=payload.username,
                ip_address=ip,
                fail_count=new_fail_count,
                window_minutes=settings.rate_limit_window_minutes,
                lockout_minutes=settings.rate_limit_lockout_minutes,
            )

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    db.add(LoginAttempt(username=payload.username, ip_address=ip, success=True))

    now = datetime.now(timezone.utc)
    session_obj = SessionModel(
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(minutes=settings.session_timeout_minutes),
        ip_address=ip,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=str(session_obj.id),
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_timeout_minutes * 60,
        path="/",
    )

    log_event(
        auth_logger,
        event="LOGIN_SUCCESS",
        level="info",
        result="success",
        message="Login successful",
        username=user.username,
        user_id=str(user.id),
        session_id=str(session_obj.id),
        ip_address=ip,
    )
    log_event(
        app_logger,
        event="login_success",
        level="info",
        result="success",
        message="Login successful",
        user_id=str(user.id),
        session_id=str(session_obj.id),
    )

    return {"id": str(user.id), "username": user.username}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DBSession = Depends(get_db)):
    raw_session_id = request.cookies.get(settings.session_cookie_name)

    if raw_session_id:
        try:
            session_uuid = UUID(raw_session_id)
        except ValueError:
            session_uuid = None

        if session_uuid is not None:
            session_obj = db.get(SessionModel, session_uuid)
            if session_obj and session_obj.revoked_at is None:
                session_obj.revoked_at = datetime.now(timezone.utc)
                db.commit()

                log_event(
                    auth_logger,
                    event="LOGOUT",
                    level="info",
                    result="success",
                    message="User logged out",
                    user_id=str(session_obj.user_id),
                    session_id=str(session_obj.id),
                )
                log_event(
                    app_logger,
                    event="logout",
                    level="info",
                    result="success",
                    message="User logged out",
                    user_id=str(session_obj.user_id),
                )

    response.delete_cookie(key=settings.session_cookie_name, path="/")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
