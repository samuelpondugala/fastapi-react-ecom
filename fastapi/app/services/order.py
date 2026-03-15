import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.address import Address
from app.models.cart import Cart, CartItem
from app.models.inventory import InventoryMovement
from app.models.order import Coupon, Order, OrderCoupon, OrderItem
from app.models.product import ProductVariant
from app.services.cart import get_or_create_active_cart

FREE_DELIVERY_THRESHOLD = Decimal("1000.00")
DELIVERY_CHARGE = Decimal("100.00")


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _next_order_number() -> str:
    suffix = uuid.uuid4().hex[:10].upper()
    return f"ORD-{suffix}"


def _calculate_shipping(subtotal: Decimal) -> Decimal:
    if subtotal >= FREE_DELIVERY_THRESHOLD:
        return Decimal("0.00")
    return DELIVERY_CHARGE


def _calculate_coupon_discount(subtotal: Decimal, coupon: Coupon | None) -> Decimal:
    if not coupon:
        return Decimal("0.00")

    if coupon.type == "fixed":
        return _money(min(Decimal(coupon.value), subtotal))
    if coupon.type == "percent":
        return _money(subtotal * (Decimal(coupon.value) / Decimal("100.00")))
    return Decimal("0.00")


def _get_valid_coupon(db: Session, coupon_code: str | None, subtotal: Decimal) -> Coupon | None:
    if not coupon_code:
        return None

    normalized = coupon_code.strip().upper()
    coupon = db.scalar(select(Coupon).where(Coupon.code.ilike(normalized), Coupon.is_active.is_(True)))
    if not coupon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found or inactive")

    now = datetime.now(timezone.utc)
    starts_at = coupon.starts_at
    expires_at = coupon.expires_at
    if starts_at and starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if starts_at and starts_at > now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon is not active yet")
    if expires_at and expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coupon has expired")

    if coupon.min_order_amount is not None and subtotal < Decimal(coupon.min_order_amount):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Coupon requires minimum order amount of {coupon.min_order_amount}",
        )

    return coupon


def create_order_from_active_cart(
    db: Session,
    user_id: int,
    shipping_address_id: int | None,
    billing_address_id: int | None,
    shipping_total: Decimal,
    tax_total: Decimal,
    coupon_code: str | None = None,
) -> Order:
    cart = db.scalar(
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.variant).selectinload(ProductVariant.product))
        .where(Cart.user_id == user_id, Cart.status == "active")
    )
    if not cart or not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    if shipping_address_id is not None:
        shipping_address = db.scalar(
            select(Address).where(Address.id == shipping_address_id, Address.user_id == user_id)
        )
        if not shipping_address:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipping address not found")

    if billing_address_id is not None:
        billing_address = db.scalar(
            select(Address).where(Address.id == billing_address_id, Address.user_id == user_id)
        )
        if not billing_address:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Billing address not found")

    subtotal = _money(sum((item.unit_price * item.quantity for item in cart.items), start=Decimal("0.00")))
    coupon = _get_valid_coupon(db, coupon_code, subtotal)
    discount_total = _calculate_coupon_discount(subtotal, coupon)
    # Taxes are applied at payment time. Keep order untaxed at checkout.
    tax_total = Decimal("0.00")
    shipping_total = _money(_calculate_shipping(subtotal))
    grand_total = _money(subtotal - discount_total + tax_total + shipping_total)

    order = Order(
        user_id=user_id,
        order_number=_next_order_number(),
        status="placed",
        payment_status="unpaid",
        fulfillment_status="unfulfilled",
        subtotal=subtotal,
        discount_total=discount_total,
        tax_total=tax_total,
        shipping_total=shipping_total,
        grand_total=grand_total,
        shipping_address_id=shipping_address_id,
        billing_address_id=billing_address_id,
    )
    db.add(order)
    db.flush()

    for cart_item in cart.items:
        variant = cart_item.variant
        product_name = variant.product.name if variant and variant.product else "Unknown Product"
        sku = variant.sku if variant else "N/A"

        line_total = _money(cart_item.unit_price * cart_item.quantity)

        order_item = OrderItem(
            order_id=order.id,
            variant_id=cart_item.variant_id,
            product_name_snapshot=product_name,
            sku_snapshot=sku,
            quantity=cart_item.quantity,
            unit_price=cart_item.unit_price,
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            line_total=line_total,
        )
        db.add(order_item)

        db.add(
            InventoryMovement(
                variant_id=cart_item.variant_id,
                type="out",
                quantity=cart_item.quantity,
                reference_type="order",
                reference_id=order.id,
                note=f"Reserved for order {order.order_number}",
            )
        )

    if coupon:
        db.add(
            OrderCoupon(
                order_id=order.id,
                coupon_id=coupon.id,
                discount_amount=discount_total,
            )
        )

    for cart_item in list(cart.items):
        db.delete(cart_item)

    cart.status = "converted"

    db.flush()
    db.refresh(order)
    return order


def restore_unpaid_order_to_cart(db: Session, order: Order) -> Cart:
    paid_states = {"paid", "captured"}
    if order.payment_status == "paid" or any((payment.status or "").lower() in paid_states for payment in order.payments):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Paid orders cannot be cancelled")

    cart = get_or_create_active_cart(db, order.user_id)
    existing_items = {item.variant_id: item for item in cart.items}

    for order_item in order.items:
        cart_item = existing_items.get(order_item.variant_id)
        if cart_item:
            cart_item.quantity += order_item.quantity
            cart_item.unit_price = order_item.unit_price
            db.add(cart_item)
            continue

        db.add(
            CartItem(
                cart_id=cart.id,
                variant_id=order_item.variant_id,
                quantity=order_item.quantity,
                unit_price=order_item.unit_price,
            )
        )

    movements = db.scalars(
        select(InventoryMovement).where(
            InventoryMovement.reference_type == "order",
            InventoryMovement.reference_id == order.id,
        )
    ).all()
    for movement in movements:
        db.delete(movement)

    db.delete(order)
    db.flush()
    db.refresh(cart)
    return cart
