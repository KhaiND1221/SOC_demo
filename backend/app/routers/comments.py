from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.logging_config import app_logger, log_event
from app.models import TaskComment, User
from app.routers.tasks import get_owned_task
from app.schemas import CommentCreate, CommentOut

router = APIRouter(prefix="/api/tasks", tags=["comments"])


@router.post("/{task_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    task_id: UUID,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    task = get_owned_task(task_id, current_user, db)

    comment = TaskComment(task_id=task.id, user_id=current_user.id, content=payload.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Logged only after db.commit() above has returned successfully - if the
    # commit raised (constraint violation, connection drop, etc.), execution
    # never reaches this line, so the log can never claim a write succeeded
    # when it did not actually persist ("log on commit", not "log on request").
    log_event(
        app_logger,
        event="comment_create",
        level="info",
        result="success",
        message="Comment created",
        user_id=str(current_user.id),
        task_id=str(task.id),
        comment_id=str(comment.id),
    )

    return comment


@router.get("/{task_id}/comments", response_model=list[CommentOut])
def list_comments(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    task = get_owned_task(task_id, current_user, db)

    comments = (
        db.query(TaskComment)
        .filter(TaskComment.task_id == task.id)
        .order_by(TaskComment.created_at)
        .all()
    )

    log_event(
        app_logger,
        event="comment_read",
        level="info",
        result="success",
        message="Comment list read",
        user_id=str(current_user.id),
        task_id=str(task.id),
        count=len(comments),
    )

    return comments


@router.delete("/{task_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    task_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    task = get_owned_task(task_id, current_user, db)

    comment = db.get(TaskComment, comment_id)
    if comment is None or comment.task_id != task.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    db.delete(comment)
    db.commit()

    # Same "log after commit" rule as create_comment above.
    log_event(
        app_logger,
        event="comment_delete",
        level="info",
        result="success",
        message="Comment deleted",
        user_id=str(current_user.id),
        task_id=str(task.id),
        comment_id=str(comment_id),
    )
