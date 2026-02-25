from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CouponCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64)
    type: str = Field(pattern="^(percent|fixed)$")
    value: Decimal = Field(gt=0)
    min_order_amount: Decimal | None = Field(default=None, ge=0)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    usage_limit: int | None = Field(default=None, ge=1)
    is_active: bool = True


class CouponRead(ORMModel):
    id: int
    code: str
    type: str
    value: Decimal
    min_order_amount: Decimal | None
    starts_at: datetime | None
    expires_at: datetime | None
    usage_limit: int | None
    is_active: bool
