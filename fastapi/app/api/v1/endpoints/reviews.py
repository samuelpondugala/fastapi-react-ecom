from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductVariant
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewRead

router = APIRouter()


@router.get("/product/{product_id}", response_model=list[ReviewRead])
def list_product_reviews(product_id: int, db: Session = Depends(get_db)) -> list[Review]:
    return list(db.scalars(select(Review).where(Review.product_id == product_id).order_by(Review.id.desc())).all())


@router.post("", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Review:
    product = db.scalar(select(Product).where(Product.id == payload.product_id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    existing = db.scalar(
        select(Review).where(Review.user_id == current_user.id, Review.product_id == payload.product_id)
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already reviewed this product")

    verified_purchase = bool(
        db.scalar(
            select(OrderItem.id)
            .join(Order, OrderItem.order_id == Order.id)
            .join(ProductVariant, OrderItem.variant_id == ProductVariant.id)
            .where(
                Order.user_id == current_user.id,
                ProductVariant.product_id == payload.product_id,
            )
            .limit(1)
        )
    )

    review = Review(
        user_id=current_user.id,
        product_id=payload.product_id,
        rating=payload.rating,
        title=payload.title,
        comment=payload.comment,
        is_verified_purchase=verified_purchase,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review
