from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ProductImageBase(BaseModel):
    image_url: str = Field(min_length=5, max_length=500)
    alt_text: str | None = None
    sort_order: int = 0
    is_primary: bool = False


class ProductImageCreate(ProductImageBase):
    pass


class ProductImageRead(ProductImageBase, ORMModel):
    id: int
    product_id: int


class ProductVariantBase(BaseModel):
    sku: str = Field(min_length=2, max_length=120)
    attributes_json: dict = Field(default_factory=dict)
    price: Decimal = Field(gt=0)
    compare_at_price: Decimal | None = None
    currency: str = Field(default="INR", min_length=3, max_length=3)
    weight: Decimal | None = None
    is_active: bool = True


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantRead(ProductVariantBase, ORMModel):
    id: int
    product_id: int
    created_at: datetime


class ProductBase(BaseModel):
    category_id: int
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=255)
    description: str | None = None
    brand: str | None = None
    status: str = "active"


class ProductCreate(ProductBase):
    images: list[ProductImageCreate] = []
    variants: list[ProductVariantCreate] = []


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=255)
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    brand: str | None = None
    status: str | None = None


class ProductRead(ProductBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageRead] = []
    variants: list[ProductVariantRead] = []
