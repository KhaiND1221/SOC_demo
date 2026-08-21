from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.deps import get_current_user
from app.logging_config import app_logger, log_event
from app.models import Order, User
from app.schemas import OrderCreate, OrderOut, OrderUpdate

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _get_owned_order(order_id: UUID, current_user: User, db: DBSession) -> Order:
    order = db.get(Order, order_id)

    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order.user_id != current_user.id:
        log_event(
            app_logger,
            event="authorization_denied",
            level="warning",
            result="fail",
            message="User attempted to access another user's order",
            resource="order",
            resource_id=str(order_id),
            owner_id=str(order.user_id),
            requester_id=str(current_user.id),
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this order")

    return order


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    order = Order(user_id=current_user.id, **payload.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)

    log_event(
        app_logger,
        event="order_create",
        level="info",
        result="success",
        message="Order created",
        user_id=str(current_user.id),
        order_id=str(order.id),
        product_name=order.product_name,
        quantity=order.quantity,
    )

    return order


@router.get("", response_model=list[OrderOut])
def list_orders(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    orders = db.query(Order).filter(Order.user_id == current_user.id).all()

    log_event(
        app_logger,
        event="order_read",
        level="info",
        result="success",
        message="Order list read",
        user_id=str(current_user.id),
        count=len(orders),
    )

    return orders


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    order = _get_owned_order(order_id, current_user, db)

    log_event(
        app_logger,
        event="order_read",
        level="info",
        result="success",
        message="Order read",
        user_id=str(current_user.id),
        order_id=str(order.id),
    )

    return order


@router.put("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: UUID,
    payload: OrderUpdate,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    order = _get_owned_order(order_id, current_user, db)

    changed_fields = {}
    updates = payload.model_dump(exclude_unset=True)

    for field, new_value in updates.items():
        old_value = getattr(order, field)
        if old_value != new_value:
            changed_fields[field] = {"old": str(old_value), "new": str(new_value)}
            setattr(order, field, new_value)

    db.commit()
    db.refresh(order)

    log_event(
        app_logger,
        event="order_update",
        level="info",
        result="success",
        message="Order updated",
        user_id=str(current_user.id),
        order_id=str(order.id),
        changed_fields=changed_fields,
    )

    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    order = _get_owned_order(order_id, current_user, db)

    db.delete(order)
    db.commit()

    log_event(
        app_logger,
        event="order_delete",
        level="info",
        result="success",
        message="Order deleted",
        user_id=str(current_user.id),
        order_id=str(order_id),
    )
