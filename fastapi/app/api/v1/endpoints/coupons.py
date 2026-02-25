from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.models.order import Coupon
from app.models.user import User
from app.schemas.coupon import CouponCreate, CouponRead

router = APIRouter()


@router.get("", response_model=list[CouponRead])
def list_coupons(
    db: Session = Depends(get_db),
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
) -> list[Coupon]:
    statement = select(Coupon)
    if active_only:
        statement = statement.where(Coupon.is_active.is_(True))
    statement = statement.order_by(Coupon.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(statement).all())


@router.post("", response_model=CouponRead, status_code=status.HTTP_201_CREATED)
def create_coupon(
    payload: CouponCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> Coupon:
    existing = db.scalar(select(Coupon).where(Coupon.code == payload.code))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Coupon code already exists")

    coupon = Coupon(**payload.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon
