from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.logging_config import app_logger, log_event
from app.models import Task, User
from app.schemas import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _get_owned_task(task_id: UUID, current_user: User, db: DBSession) -> Task:
    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.user_id != current_user.id:
        log_event(
            app_logger,
            event="authorization_denied",
            level="warning",
            result="fail",
            message="User attempted to access another user's task",
            resource="task",
            resource_id=str(task_id),
            owner_id=str(task.user_id),
            requester_id=str(current_user.id),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this task")

    return task


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    task = Task(user_id=current_user.id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)

    log_event(
        app_logger,
        event="task_create",
        level="info",
        result="success",
        message="Task created",
        user_id=str(current_user.id),
        task_id=str(task.id),
        title=task.title,
        priority=task.priority,
    )

    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    tasks = db.query(Task).filter(Task.user_id == current_user.id).all()

    log_event(
        app_logger,
        event="task_read",
        level="info",
        result="success",
        message="Task list read",
        user_id=str(current_user.id),
        count=len(tasks),
    )

    return tasks


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)

    log_event(
        app_logger,
        event="task_read",
        level="info",
        result="success",
        message="Task read",
        user_id=str(current_user.id),
        task_id=str(task.id),
    )

    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)

    changed_fields = {}
    updates = payload.model_dump(exclude_unset=True)

    for field, new_value in updates.items():
        old_value = getattr(task, field)
        if old_value != new_value:
            changed_fields[field] = {"old": str(old_value), "new": str(new_value)}
            setattr(task, field, new_value)

    db.commit()
    db.refresh(task)

    log_event(
        app_logger,
        event="task_update",
        level="info",
        result="success",
        message="Task updated",
        user_id=str(current_user.id),
        task_id=str(task.id),
        changed_fields=changed_fields,
    )

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    task = _get_owned_task(task_id, current_user, db)

    db.delete(task)
    db.commit()

    log_event(
        app_logger,
        event="task_delete",
        level="info",
        result="success",
        message="Task deleted",
        user_id=str(current_user.id),
        task_id=str(task_id),
    )
