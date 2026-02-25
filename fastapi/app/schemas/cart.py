from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CartItemCreate(BaseModel):
    variant_id: int
    quantity: int = Field(default=1, ge=1, le=100)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=100)


class CartItemRead(ORMModel):
    id: int
    cart_id: int
    variant_id: int
    variant_sku: str | None = None
    product_id: int | None = None
    product_name: str | None = None
    product_slug: str | None = None
    product_image_url: str | None = None
    product_image_alt: str | None = None
    quantity: int
    unit_price: Decimal
    added_at: datetime


class CartRead(ORMModel):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: datetime
    items: list[CartItemRead] = []
