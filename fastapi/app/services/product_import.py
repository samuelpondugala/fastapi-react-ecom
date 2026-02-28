from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.category import Category
from app.models.product import Product, ProductImage, ProductVariant

USD_TO_INR_RATE = Decimal("83.00")


@dataclass
class NormalizedProduct:
    name: str
    slug: str
    description: str | None
    brand: str | None
    status: str
    category_name: str
    sku: str
    price: Decimal
    compare_at_price: Decimal | None
    currency: str
    weight: Decimal | None
    images: list[str]
    attributes: dict[str, Any]


def fetch_dummyjson_products(*, limit: int, skip: int) -> list[dict[str, Any]]:
    query = urlencode({"limit": limit, "skip": skip})
    url = f"https://dummyjson.com/products?{query}"
    request = Request(url, headers={"User-Agent": "ecom-fastapi-importer/1.0"})
    with urlopen(request, timeout=20) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))

    products = payload.get("products", [])
    if not isinstance(products, list):
        raise ValueError("dummyjson response does not contain products list")
    return products


def import_products_from_records(
    db: Session,
    *,
    records: list[dict[str, Any]],
    source: str,
    update_existing: bool,
    default_category_name: str,
) -> dict[str, Any]:
    result = {
        "source": source,
        "total_input": len(records),
        "created_products": 0,
        "updated_products": 0,
        "skipped_products": 0,
        "created_categories": 0,
        "errors": [],
    }

    categories_by_slug = {
        category.slug: category
        for category in db.scalars(select(Category).order_by(Category.id)).all()
    }

    for index, item in enumerate(records, start=1):
        savepoint = db.begin_nested()
        try:
            normalized = _normalize_product(
                item=item,
                index=index,
                source=source,
                default_category_name=default_category_name,
            )

            category, category_created = _get_or_create_category(
                db=db,
                categories_by_slug=categories_by_slug,
                category_name=normalized.category_name,
            )
            if category_created:
                result["created_categories"] += 1

            action = _upsert_product(
                db=db,
                normalized=normalized,
                category_id=category.id,
                update_existing=update_existing,
            )

            if action == "created":
                result["created_products"] += 1
            elif action == "updated":
                result["updated_products"] += 1
            else:
                result["skipped_products"] += 1

            savepoint.commit()
        except Exception as exc:  # noqa: BLE001
            savepoint.rollback()
            result["errors"].append(f"#{index}: {exc}")

    return result


def _normalize_product(
    *,
    item: dict[str, Any],
    index: int,
    source: str,
    default_category_name: str,
) -> NormalizedProduct:
    name = str(item.get("title") or item.get("name") or "").strip()
    if not name:
        raise ValueError("missing title/name")

    category_name = str(item.get("category") or default_category_name).strip() or default_category_name
    slug = str(item.get("slug") or "").strip()
    if not slug:
        slug = _slugify(name)
    if not slug:
        slug = f"imported-product-{index}"

    sku = str(item.get("sku") or "").strip()
    if not sku:
        sku = f"IMP-{_slugify(name).upper()[:30]}-{index:04d}"

    usd_price = _to_decimal(item.get("price"))
    if usd_price <= Decimal("0.00"):
        raise ValueError("price must be > 0")
    price = _money(usd_price * USD_TO_INR_RATE)

    discount = _to_decimal(item.get("discountPercentage") or 0)
    compare_at_price = None
    if Decimal("0.00") < discount < Decimal("100.00"):
        compare_at_price = _money(price / (Decimal("1.00") - (discount / Decimal("100.00"))))

    weight = _to_optional_decimal(item.get("weight"))
    if weight is not None:
        weight = _money(weight)

    images = _normalize_images(item)
    description = _to_optional_text(item.get("description"))
    brand = _to_optional_text(item.get("brand"))

    attributes = _compact_dict(
        {
            "source": source,
            "source_id": item.get("id"),
            "source_price_usd": str(_money(usd_price)),
            "usd_to_inr_rate": str(USD_TO_INR_RATE),
            "rating": item.get("rating"),
            "stock": item.get("stock"),
            "tags": item.get("tags"),
            "dimensions": item.get("dimensions"),
            "availability_status": item.get("availabilityStatus"),
            "minimum_order_quantity": item.get("minimumOrderQuantity"),
            "warranty_information": item.get("warrantyInformation"),
            "shipping_information": item.get("shippingInformation"),
        }
    )

    return NormalizedProduct(
        name=name,
        slug=slug,
        description=description,
        brand=brand,
        status="active",
        category_name=category_name,
        sku=sku,
        price=price,
        compare_at_price=compare_at_price,
        currency="INR",
        weight=weight,
        images=images,
        attributes=attributes,
    )


def _upsert_product(
    *,
    db: Session,
    normalized: NormalizedProduct,
    category_id: int,
    update_existing: bool,
) -> str:
    existing_variant = db.scalar(select(ProductVariant).where(ProductVariant.sku == normalized.sku))
    existing_product = None
    if existing_variant:
        existing_product = _load_product(db, existing_variant.product_id)
    if existing_product is None:
        existing_by_slug = db.scalar(select(Product).where(Product.slug == normalized.slug))
        if existing_by_slug:
            existing_product = _load_product(db, existing_by_slug.id)

    if existing_product and not update_existing:
        return "skipped"

    if existing_product:
        existing_product.category_id = category_id
        existing_product.name = normalized.name
        existing_product.slug = normalized.slug
        existing_product.description = normalized.description
        existing_product.brand = normalized.brand
        existing_product.status = normalized.status

        variant = (
            next((item for item in existing_product.variants if item.sku == normalized.sku), None)
            or (existing_product.variants[0] if existing_product.variants else None)
        )
        if variant:
            if variant.sku != normalized.sku:
                variant.sku = _ensure_unique_sku(db, normalized.sku, current_variant_id=variant.id)
            variant.price = normalized.price
            variant.compare_at_price = normalized.compare_at_price
            variant.currency = normalized.currency
            variant.weight = normalized.weight
            variant.attributes_json = normalized.attributes
            variant.is_active = True
        else:
            existing_product.variants.append(
                ProductVariant(
                    sku=_ensure_unique_sku(db, normalized.sku),
                    price=normalized.price,
                    compare_at_price=normalized.compare_at_price,
                    currency=normalized.currency,
                    weight=normalized.weight,
                    attributes_json=normalized.attributes,
                    is_active=True,
                )
            )

        _replace_images(existing_product, normalized.images)
        db.add(existing_product)
        db.flush()
        return "updated"

    product_slug = _ensure_unique_slug(db, normalized.slug)
    product_sku = _ensure_unique_sku(db, normalized.sku)

    product = Product(
        category_id=category_id,
        name=normalized.name,
        slug=product_slug,
        description=normalized.description,
        brand=normalized.brand,
        status=normalized.status,
    )
    db.add(product)
    db.flush()

    for image_index, url in enumerate(normalized.images):
        product.images.append(
            ProductImage(
                image_url=url,
                alt_text=normalized.name,
                sort_order=image_index,
                is_primary=image_index == 0,
            )
        )

    product.variants.append(
        ProductVariant(
            sku=product_sku,
            price=normalized.price,
            compare_at_price=normalized.compare_at_price,
            currency=normalized.currency,
            weight=normalized.weight,
            attributes_json=normalized.attributes,
            is_active=True,
        )
    )
    db.add(product)
    db.flush()
    return "created"


def _replace_images(product: Product, image_urls: list[str]) -> None:
    product.images.clear()
    for image_index, url in enumerate(image_urls):
        product.images.append(
            ProductImage(
                image_url=url,
                alt_text=product.name,
                sort_order=image_index,
                is_primary=image_index == 0,
            )
        )


def _get_or_create_category(
    *,
    db: Session,
    categories_by_slug: dict[str, Category],
    category_name: str,
) -> tuple[Category, bool]:
    base_slug = _slugify(category_name) or "imported"
    category = categories_by_slug.get(base_slug)
    if category:
        return category, False

    category = Category(
        name=category_name.title(),
        slug=base_slug,
        description=f"Imported category for {category_name}",
        is_active=True,
    )
    db.add(category)
    db.flush()
    categories_by_slug[category.slug] = category
    return category, True


def _load_product(db: Session, product_id: int) -> Product:
    product = db.scalar(
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.variants))
        .where(Product.id == product_id)
    )
    if not product:
        raise ValueError(f"Product not found: {product_id}")
    return product


def _ensure_unique_slug(db: Session, base_slug: str) -> str:
    slug = base_slug
    counter = 2
    while db.scalar(select(Product.id).where(Product.slug == slug)):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def _ensure_unique_sku(db: Session, base_sku: str, current_variant_id: int | None = None) -> str:
    sku = base_sku
    counter = 2
    while True:
        existing = db.scalar(select(ProductVariant).where(ProductVariant.sku == sku))
        if not existing or (current_variant_id is not None and existing.id == current_variant_id):
            return sku
        sku = f"{base_sku}-{counter}"
        counter += 1


def _slugify(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"invalid decimal value: {value}") from exc


def _to_optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return _to_decimal(value)


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _to_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_images(item: dict[str, Any]) -> list[str]:
    images: list[str] = []
    thumbnail = _to_optional_text(item.get("thumbnail"))
    if thumbnail:
        images.append(thumbnail)

    raw_images = item.get("images")
    if isinstance(raw_images, list):
        for raw in raw_images:
            image = _to_optional_text(raw)
            if image and image not in images:
                images.append(image)
    return images


def _compact_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None and value != ""}
