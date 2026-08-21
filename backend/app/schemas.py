import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class OrderCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=255)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    status: str = Field(default="pending", max_length=20)


class OrderUpdate(BaseModel):
    product_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    quantity: Optional[int] = Field(default=None, gt=0)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, max_length=20)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
