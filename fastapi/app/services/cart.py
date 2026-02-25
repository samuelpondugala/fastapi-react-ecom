from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.cart import Cart, CartItem
from app.models.product import ProductVariant


def get_or_create_active_cart(db: Session, user_id: int) -> Cart:
    cart = db.scalar(
        select(Cart)
        .options(selectinload(Cart.items))
        .where(Cart.user_id == user_id, Cart.status == "active")
    )
    if cart:
        return cart

    # carts.user_id is unique, so after checkout we should reactivate the existing
    # converted cart instead of trying to insert a second cart row.
    existing_cart = db.scalar(select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user_id))
    if existing_cart:
        existing_cart.status = "active"
        db.add(existing_cart)
        db.flush()
        db.refresh(existing_cart)
        return existing_cart

    cart = Cart(user_id=user_id, status="active")
    db.add(cart)
    try:
        db.flush()
        db.refresh(cart)
        return cart
    except IntegrityError:
        # Concurrent requests may both try to create first cart row for a user.
        # If the unique constraint is hit, reload and reuse the existing row.
        db.rollback()
        cart = db.scalar(select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == user_id))
        if not cart:
            raise
        if cart.status != "active":
            cart.status = "active"
            db.add(cart)
            db.flush()
            db.refresh(cart)
        return cart


def add_cart_item(db: Session, cart: Cart, variant_id: int, quantity: int) -> CartItem:
    variant = db.scalar(select(ProductVariant).where(ProductVariant.id == variant_id, ProductVariant.is_active.is_(True)))
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found")

    item = db.scalar(select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant_id))
    if item:
        item.quantity += quantity
        item.unit_price = Decimal(variant.price)
    else:
        item = CartItem(
            cart_id=cart.id,
            variant_id=variant_id,
            quantity=quantity,
            unit_price=Decimal(variant.price),
        )
        db.add(item)

    db.flush()
    db.refresh(item)
    return item


def update_cart_item_quantity(db: Session, cart_id: int, item_id: int, quantity: int) -> CartItem:
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart_id))
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")

    item.quantity = quantity
    db.flush()
    db.refresh(item)
    return item


def delete_cart_item(db: Session, cart_id: int, item_id: int) -> None:
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart_id))
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart item not found")
    db.delete(item)
    db.flush()


def clear_cart(db: Session, cart_id: int) -> int:
    items = db.scalars(select(CartItem).where(CartItem.cart_id == cart_id)).all()
    deleted = len(items)
    for item in items:
        db.delete(item)
    db.flush()
    return deleted
