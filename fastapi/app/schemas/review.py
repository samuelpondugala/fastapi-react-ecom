from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=255)
    comment: str | None = None


class ReviewRead(ORMModel):
    id: int
    user_id: int
    product_id: int
    rating: int
    title: str | None
    comment: str | None
    is_verified_purchase: bool
    created_at: datetime
    updated_at: datetime
