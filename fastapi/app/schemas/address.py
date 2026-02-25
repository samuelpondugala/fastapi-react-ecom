from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class AddressBase(BaseModel):
    label: str | None = None
    line1: str = Field(min_length=2, max_length=255)
    line2: str | None = None
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    country: str = Field(min_length=1, max_length=100)
    is_default: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    label: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    is_default: bool | None = None


class AddressRead(AddressBase, ORMModel):
    id: int
    user_id: int
    created_at: datetime
