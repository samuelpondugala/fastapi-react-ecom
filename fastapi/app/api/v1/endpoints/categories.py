from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.cache import get_cached, invalidate_namespace, set_cached

router = APIRouter()


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: Session = Depends(get_db),
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[CategoryRead]:
    cached = get_cached(
        "categories:list",
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    if isinstance(cached, list):
        return [CategoryRead.model_validate(item) for item in cached]

    statement = select(Category)
    if not include_inactive:
        statement = statement.where(Category.is_active.is_(True))
    statement = statement.order_by(Category.name).offset(offset).limit(limit)
    categories = list(db.scalars(statement).all())
    payload = [CategoryRead.model_validate(item).model_dump(mode="json") for item in categories]
    set_cached(
        "categories:list",
        payload,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
    )
    return [CategoryRead.model_validate(item) for item in categories]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> Category:
    existing = db.scalar(select(Category).where(Category.slug == payload.slug))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category slug already exists")

    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    invalidate_namespace("categories:list")
    return category


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> Category:
    category = db.scalar(select(Category).where(Category.id == category_id))
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    updates = payload.model_dump(exclude_unset=True)
    if "slug" in updates:
        duplicate = db.scalar(select(Category).where(Category.slug == updates["slug"], Category.id != category_id))
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category slug already exists")

    for key, value in updates.items():
        setattr(category, key, value)

    db.add(category)
    db.commit()
    db.refresh(category)
    invalidate_namespace("categories:list")
    return category
