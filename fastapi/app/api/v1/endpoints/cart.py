from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.schemas.cart import CartItemCreate, CartItemUpdate, CartRead
from app.services.cart import add_cart_item, clear_cart, delete_cart_item, get_or_create_active_cart, update_cart_item_quantity

router = APIRouter()


def _load_cart(db: Session, cart_id: int) -> Cart:
    cart = db.scalar(
        select(Cart)
        .options(
            selectinload(Cart.items)
            .selectinload(CartItem.variant)
            .selectinload(ProductVariant.product)
            .selectinload(Product.images)
        )
        .where(Cart.id == cart_id)
    )
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    return cart


@router.get("/me", response_model=CartRead)
def get_my_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Cart:
    cart = get_or_create_active_cart(db, current_user.id)
    db.commit()
    return _load_cart(db, cart.id)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
def add_item(
    payload: CartItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Cart:
    cart = get_or_create_active_cart(db, current_user.id)
    add_cart_item(db, cart, payload.variant_id, payload.quantity)
    db.commit()
    return _load_cart(db, cart.id)


@router.patch("/items/{item_id}", response_model=CartRead)
def update_item(
    item_id: int,
    payload: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Cart:
    cart = get_or_create_active_cart(db, current_user.id)
    update_cart_item_quantity(db, cart.id, item_id, payload.quantity)
    db.commit()
    return _load_cart(db, cart.id)


@router.delete("/items/{item_id}", response_model=CartRead)
def remove_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Cart:
    cart = get_or_create_active_cart(db, current_user.id)
    delete_cart_item(db, cart.id, item_id)
    db.commit()
    return _load_cart(db, cart.id)


@router.delete("/clear", response_model=dict[str, int])
def clear_my_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    cart = get_or_create_active_cart(db, current_user.id)
    deleted = clear_cart(db, cart.id)
    db.commit()
    return {"deleted_items": deleted}
