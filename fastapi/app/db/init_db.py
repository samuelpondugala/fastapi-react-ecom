from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User


def ensure_default_admin(db: Session) -> bool:
    settings = get_settings()
    admin = db.scalar(select(User).where(User.email == settings.DEFAULT_ADMIN_EMAIL))
    created = False
    if not admin:
        admin = User(email=settings.DEFAULT_ADMIN_EMAIL)
        db.add(admin)
        created = True

    # Keep default admin aligned with environment values when seed runs.
    admin.password_hash = get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)
    admin.role = "admin"
    admin.is_active = True
    if not admin.full_name:
        admin.full_name = "Default Admin"

    db.commit()
    return created


def ensure_demo_users(db: Session) -> dict[str, bool]:
    settings = get_settings()
    created = {"demo_admin": False, "demo_vendor": False}
    if not settings.SEED_DEMO_USERS:
        return created

    demo_admin = db.scalar(select(User).where(User.email == settings.DEMO_ADMIN_EMAIL))
    legacy_demo_admin = db.scalar(select(User).where(User.email == "ecomadmin@ecom.local"))
    if not demo_admin and legacy_demo_admin:
        demo_admin = legacy_demo_admin
        demo_admin.email = settings.DEMO_ADMIN_EMAIL
        created["demo_admin"] = True
    if not demo_admin:
        demo_admin = User(email=settings.DEMO_ADMIN_EMAIL)
        db.add(demo_admin)
        created["demo_admin"] = True

    demo_admin.password_hash = get_password_hash(settings.DEMO_ADMIN_PASSWORD)
    demo_admin.role = "admin"
    demo_admin.is_active = True
    demo_admin.full_name = settings.DEMO_ADMIN_USERNAME

    demo_vendor = db.scalar(select(User).where(User.email == settings.DEMO_VENDOR_EMAIL))
    legacy_demo_vendor = db.scalar(select(User).where(User.email == "ecomvendor@ecom.local"))
    if not demo_vendor and legacy_demo_vendor:
        demo_vendor = legacy_demo_vendor
        demo_vendor.email = settings.DEMO_VENDOR_EMAIL
        created["demo_vendor"] = True
    if not demo_vendor:
        demo_vendor = User(email=settings.DEMO_VENDOR_EMAIL)
        db.add(demo_vendor)
        created["demo_vendor"] = True

    demo_vendor.password_hash = get_password_hash(settings.DEMO_VENDOR_PASSWORD)
    demo_vendor.role = "vendor"
    demo_vendor.is_active = True
    demo_vendor.full_name = settings.DEMO_VENDOR_USERNAME

    db.commit()

    return created
