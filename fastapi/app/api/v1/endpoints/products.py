from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_staff_user
from app.db.session import get_db
from app.models.category import Category
from app.models.product import Product, ProductImage, ProductVariant
from app.models.user import User
from app.schemas.importer import DummyJsonImportRequest, JsonProductImportRequest, ProductImportResult
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.cache import get_cached, invalidate_namespace, set_cached
from app.services.product_import import fetch_dummyjson_products, import_products_from_records

router = APIRouter()


@router.get("", response_model=list[ProductRead])
def list_products(
    db: Session = Depends(get_db),
    category_id: int | None = None,
    status_filter: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ProductRead]:
    cached = get_cached(
        "products:list",
        category_id=category_id,
        status_filter=status_filter,
        q=q,
        limit=limit,
        offset=offset,
    )
    if isinstance(cached, list):
        return [ProductRead.model_validate(item) for item in cached]

    statement = (
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.variants))
        .order_by(Product.id.desc())
    )
    if category_id is not None:
        statement = statement.where(Product.category_id == category_id)
    if status_filter is not None:
        statement = statement.where(Product.status == status_filter)
    if q:
        statement = statement.where(Product.name.ilike(f"%{q}%"))

    statement = statement.offset(offset).limit(limit)
    products = list(db.scalars(statement).all())
    payload = [ProductRead.model_validate(item).model_dump(mode="json") for item in products]
    set_cached(
        "products:list",
        payload,
        category_id=category_id,
        status_filter=status_filter,
        q=q,
        limit=limit,
        offset=offset,
    )
    return [ProductRead.model_validate(item) for item in products]


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductRead:
    cached = get_cached("products:detail", product_id=product_id)
    if isinstance(cached, dict):
        return ProductRead.model_validate(cached)

    product = db.scalar(
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.variants))
        .where(Product.id == product_id)
    )
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    payload = ProductRead.model_validate(product)
    set_cached("products:detail", payload.model_dump(mode="json"), product_id=product_id)
    return payload


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_staff_user),
) -> Product:
    category = db.scalar(select(Category).where(Category.id == payload.category_id))
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    duplicate_slug = db.scalar(select(Product).where(Product.slug == payload.slug))
    if duplicate_slug:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product slug already exists")

    product = Product(
        category_id=payload.category_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        brand=payload.brand,
        status=payload.status,
    )
    db.add(product)
    db.flush()

    for image in payload.images:
        db.add(ProductImage(product_id=product.id, **image.model_dump()))

    for variant in payload.variants:
        existing_sku = db.scalar(select(ProductVariant).where(ProductVariant.sku == variant.sku))
        if existing_sku:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"SKU already exists: {variant.sku}")
        db.add(ProductVariant(product_id=product.id, **variant.model_dump()))

    db.commit()
    db.refresh(product)
    invalidate_namespace("products:list")
    invalidate_namespace("products:detail")
    return db.scalar(
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.variants))
        .where(Product.id == product.id)
    )


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_staff_user),
) -> Product:
    product = db.scalar(select(Product).where(Product.id == product_id))
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)

    if "slug" in updates:
        duplicate = db.scalar(select(Product).where(Product.slug == updates["slug"], Product.id != product_id))
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product slug already exists")

    if "category_id" in updates:
        category = db.scalar(select(Category).where(Category.id == updates["category_id"]))
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    for key, value in updates.items():
        setattr(product, key, value)

    db.add(product)
    db.commit()
    db.refresh(product)
    invalidate_namespace("products:list")
    invalidate_namespace("products:detail")
    return db.scalar(
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.variants))
        .where(Product.id == product.id)
    )


@router.post(
    "/import/dummyjson",
    response_model=ProductImportResult,
    summary="Import products from DummyJSON",
    description=(
        "Fetches products from https://dummyjson.com/products and imports them into the catalog. "
        "Available to admin and vendor roles."
    ),
)
def import_dummyjson(
    payload: DummyJsonImportRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_staff_user),
) -> ProductImportResult:
    try:
        products = fetch_dummyjson_products(limit=payload.limit, skip=payload.skip)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch dummyjson products: {exc}",
        ) from exc
    report = import_products_from_records(
        db,
        records=products,
        source="dummyjson",
        update_existing=payload.update_existing,
        default_category_name=payload.default_category_name,
    )
    db.commit()
    invalidate_namespace("products:list")
    invalidate_namespace("products:detail")
    invalidate_namespace("categories:list")
    return ProductImportResult(**report)


@router.post(
    "/import/json",
    response_model=ProductImportResult,
    summary="Import products from pasted JSON payload",
    description=(
        "Imports products from JSON in DummyJSON-compatible shape. "
        "Pass `{ \"products\": [...] }` and the backend will map fields to catalog entities."
    ),
)
def import_from_json_payload(
    payload: JsonProductImportRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_staff_user),
) -> ProductImportResult:
    report = import_products_from_records(
        db,
        records=payload.products,
        source="manual_json",
        update_existing=payload.update_existing,
        default_category_name=payload.default_category_name,
    )
    db.commit()
    invalidate_namespace("products:list")
    invalidate_namespace("products:detail")
    invalidate_namespace("categories:list")
    return ProductImportResult(**report)
