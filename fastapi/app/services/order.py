import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.address import Address
from app.models.cart import Cart, CartItem
from app.models.inventory import InventoryMovement
from app.models.order import Order, OrderItem
from app.models.product import ProductVariant


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _next_order_number() -> str:
    suffix = uuid.uuid4().hex[:10].upper()
    return f"ORD-{suffix}"


def create_order_from_active_cart(
    db: Session,
    user_id: int,
    shipping_address_id: int | None,
    billing_address_id: int | None,
    shipping_total: Decimal,
    tax_total: Decimal,
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
    discount_total = Decimal("0.00")
    # Taxes are applied at payment time. Keep order untaxed at checkout.
    tax_total = Decimal("0.00")
    shipping_total = _money(Decimal(shipping_total))
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

    for cart_item in list(cart.items):
        db.delete(cart_item)

    cart.status = "converted"

    db.flush()
    db.refresh(order)
    return order
