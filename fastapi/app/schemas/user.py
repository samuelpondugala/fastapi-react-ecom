from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.address import AddressRead
from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None
    full_name: str | None = None


class UserUpdate(BaseModel):
    phone: str | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserRead(ORMModel):
    id: int
    email: EmailStr
    phone: str | None
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserWithAddresses(UserRead):
    addresses: list[AddressRead] = []
