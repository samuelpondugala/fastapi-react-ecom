from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("cart_id", "variant_id", name="uq_cart_item_cart_variant"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cart = relationship("Cart", back_populates="items")
    variant = relationship("ProductVariant", back_populates="cart_items")

    @property
    def product_id(self) -> int | None:
        return self.variant.product_id if self.variant else None

    @property
    def product_name(self) -> str | None:
        if not self.variant or not self.variant.product:
            return None
        return self.variant.product.name

    @property
    def product_slug(self) -> str | None:
        if not self.variant or not self.variant.product:
            return None
        return self.variant.product.slug

    @property
    def variant_sku(self) -> str | None:
        return self.variant.sku if self.variant else None

    @property
    def product_image_url(self) -> str | None:
        if not self.variant or not self.variant.product or not self.variant.product.images:
            return None
        primary = next((image for image in self.variant.product.images if image.is_primary), None)
        return (primary or self.variant.product.images[0]).image_url

    @property
    def product_image_alt(self) -> str | None:
        if not self.variant or not self.variant.product or not self.variant.product.images:
            return self.product_name
        primary = next((image for image in self.variant.product.images if image.is_primary), None)
        chosen = primary or self.variant.product.images[0]
        return chosen.alt_text or self.product_name
