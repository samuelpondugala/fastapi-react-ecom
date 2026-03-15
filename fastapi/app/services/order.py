import uuid
from dataclasses import dataclass
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


@dataclass
class CheckoutSnapshotItem:
    variant_id: int
    product_name_snapshot: str
    sku_snapshot: str
    quantity: int
    unit_price: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    line_total: Decimal


@dataclass
class CheckoutSnapshot:
    user_id: int
    shipping_address_id: int | None
    billing_address_id: int | None
    coupon_id: int | None
    coupon_code: str | None
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    items: list[CheckoutSnapshotItem]


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


def _load_active_cart_for_checkout(db: Session, user_id: int) -> Cart:
    cart = db.scalar(
        select(Cart)
        .options(selectinload(Cart.items).selectinload(CartItem.variant).selectinload(ProductVariant.product))
        .where(Cart.user_id == user_id, Cart.status == "active")
    )
    if not cart or not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")
    return cart


def build_checkout_snapshot(
    db: Session,
    *,
    user_id: int,
    shipping_address_id: int | None,
    billing_address_id: int | None,
    shipping_total: Decimal,
    tax_total: Decimal,
    coupon_code: str | None = None,
) -> CheckoutSnapshot:
    cart = _load_active_cart_for_checkout(db, user_id)

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
    tax_total = Decimal("0.00")
    shipping_total = _money(_calculate_shipping(subtotal))
    grand_total = _money(subtotal - discount_total + tax_total + shipping_total)

    items: list[CheckoutSnapshotItem] = []
    for cart_item in cart.items:
        variant = cart_item.variant
        product_name = variant.product.name if variant and variant.product else "Unknown Product"
        sku = variant.sku if variant else "N/A"
        line_total = _money(cart_item.unit_price * cart_item.quantity)

        items.append(
            CheckoutSnapshotItem(
                variant_id=cart_item.variant_id,
                product_name_snapshot=product_name,
                sku_snapshot=sku,
                quantity=cart_item.quantity,
                unit_price=_money(Decimal(cart_item.unit_price)),
                tax_amount=Decimal("0.00"),
                discount_amount=Decimal("0.00"),
                line_total=line_total,
            )
        )

    return CheckoutSnapshot(
        user_id=user_id,
        shipping_address_id=shipping_address_id,
        billing_address_id=billing_address_id,
        coupon_id=coupon.id if coupon else None,
        coupon_code=coupon.code if coupon else None,
        subtotal=subtotal,
        discount_total=discount_total,
        tax_total=tax_total,
        shipping_total=shipping_total,
        grand_total=grand_total,
        items=items,
    )


def serialize_checkout_snapshot(snapshot: CheckoutSnapshot) -> dict[str, object]:
    return {
        "user_id": snapshot.user_id,
        "shipping_address_id": snapshot.shipping_address_id,
        "billing_address_id": snapshot.billing_address_id,
        "coupon_id": snapshot.coupon_id,
        "coupon_code": snapshot.coupon_code,
        "subtotal": str(snapshot.subtotal),
        "discount_total": str(snapshot.discount_total),
        "tax_total": str(snapshot.tax_total),
        "shipping_total": str(snapshot.shipping_total),
        "grand_total": str(snapshot.grand_total),
        "items": [
            {
                "variant_id": item.variant_id,
                "product_name_snapshot": item.product_name_snapshot,
                "sku_snapshot": item.sku_snapshot,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "tax_amount": str(item.tax_amount),
                "discount_amount": str(item.discount_amount),
                "line_total": str(item.line_total),
            }
            for item in snapshot.items
        ],
    }


def deserialize_checkout_snapshot(data: dict[str, object]) -> CheckoutSnapshot:
    raw_items = data.get("items") or []
    items = [
        CheckoutSnapshotItem(
            variant_id=int(item["variant_id"]),
            product_name_snapshot=str(item["product_name_snapshot"]),
            sku_snapshot=str(item["sku_snapshot"]),
            quantity=int(item["quantity"]),
            unit_price=Decimal(str(item["unit_price"])),
            tax_amount=Decimal(str(item["tax_amount"])),
            discount_amount=Decimal(str(item["discount_amount"])),
            line_total=Decimal(str(item["line_total"])),
        )
        for item in raw_items
        if isinstance(item, dict)
    ]

    return CheckoutSnapshot(
        user_id=int(data["user_id"]),
        shipping_address_id=int(data["shipping_address_id"]) if data.get("shipping_address_id") is not None else None,
        billing_address_id=int(data["billing_address_id"]) if data.get("billing_address_id") is not None else None,
        coupon_id=int(data["coupon_id"]) if data.get("coupon_id") is not None else None,
        coupon_code=str(data["coupon_code"]) if data.get("coupon_code") is not None else None,
        subtotal=Decimal(str(data["subtotal"])),
        discount_total=Decimal(str(data["discount_total"])),
        tax_total=Decimal(str(data["tax_total"])),
        shipping_total=Decimal(str(data["shipping_total"])),
        grand_total=Decimal(str(data["grand_total"])),
        items=items,
    )


def _consume_snapshot_from_active_cart(db: Session, snapshot: CheckoutSnapshot) -> None:
    cart = db.scalar(select(Cart).options(selectinload(Cart.items)).where(Cart.user_id == snapshot.user_id))
    if not cart:
        return

    cart_items_by_variant = {item.variant_id: item for item in cart.items}
    for snapshot_item in snapshot.items:
        cart_item = cart_items_by_variant.get(snapshot_item.variant_id)
        if not cart_item:
            continue

        if cart_item.quantity <= snapshot_item.quantity:
            db.delete(cart_item)
            continue

        cart_item.quantity -= snapshot_item.quantity
        db.add(cart_item)

    db.flush()
    remaining_cart_item = db.scalar(select(CartItem.id).where(CartItem.cart_id == cart.id).limit(1))
    if remaining_cart_item is None:
        cart.status = "converted"
        db.flush()


def create_order_from_snapshot(db: Session, snapshot: CheckoutSnapshot) -> Order:
    shipping_address_id = snapshot.shipping_address_id
    if shipping_address_id is not None:
        shipping_address_exists = db.scalar(select(Address.id).where(Address.id == shipping_address_id))
        if not shipping_address_exists:
            shipping_address_id = None

    billing_address_id = snapshot.billing_address_id
    if billing_address_id is not None:
        billing_address_exists = db.scalar(select(Address.id).where(Address.id == billing_address_id))
        if not billing_address_exists:
            billing_address_id = None

    order = Order(
        user_id=snapshot.user_id,
        order_number=_next_order_number(),
        status="placed",
        payment_status="unpaid",
        fulfillment_status="unfulfilled",
        subtotal=snapshot.subtotal,
        discount_total=snapshot.discount_total,
        tax_total=snapshot.tax_total,
        shipping_total=snapshot.shipping_total,
        grand_total=snapshot.grand_total,
        shipping_address_id=shipping_address_id,
        billing_address_id=billing_address_id,
    )
    db.add(order)
    db.flush()

    for item in snapshot.items:
        db.add(
            OrderItem(
                order_id=order.id,
                variant_id=item.variant_id,
                product_name_snapshot=item.product_name_snapshot,
                sku_snapshot=item.sku_snapshot,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_amount=item.tax_amount,
                discount_amount=item.discount_amount,
                line_total=item.line_total,
            )
        )

        db.add(
            InventoryMovement(
                variant_id=item.variant_id,
                type="out",
                quantity=item.quantity,
                reference_type="order",
                reference_id=order.id,
                note=f"Reserved for order {order.order_number}",
            )
        )

    if snapshot.coupon_id is not None and db.scalar(select(Coupon.id).where(Coupon.id == snapshot.coupon_id)):
        db.add(
            OrderCoupon(
                order_id=order.id,
                coupon_id=snapshot.coupon_id,
                discount_amount=snapshot.discount_total,
            )
        )

    _consume_snapshot_from_active_cart(db, snapshot)
    db.flush()
    db.refresh(order)
    return order


def create_order_from_active_cart(
    db: Session,
    user_id: int,
    shipping_address_id: int | None,
    billing_address_id: int | None,
    shipping_total: Decimal,
    tax_total: Decimal,
    coupon_code: str | None = None,
) -> Order:
    snapshot = build_checkout_snapshot(
        db,
        user_id=user_id,
        shipping_address_id=shipping_address_id,
        billing_address_id=billing_address_id,
        shipping_total=shipping_total,
        tax_total=tax_total,
        coupon_code=coupon_code,
    )
    return create_order_from_snapshot(db, snapshot)


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
