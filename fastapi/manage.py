#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_PARENT = BASE_DIR.parent

# Avoid import shadowing from /ecom/fastapi directory name.
os.chdir(BASE_DIR)
if str(PROJECT_PARENT) in sys.path:
    sys.path.remove(str(PROJECT_PARENT))
if "" in sys.path:
    sys.path.remove("")
sys.path.insert(0, str(BASE_DIR))


def _run(command: list[str]) -> None:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{BASE_DIR}{os.pathsep}{existing}" if existing else str(BASE_DIR)
    subprocess.run(command, cwd=BASE_DIR, env=env, check=True)


def cmd_run(args: argparse.Namespace) -> None:
    if args.reload and args.workers > 1:
        raise SystemExit("--reload and --workers > 1 cannot be used together")

    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--log-level",
        args.log_level,
    ]
    if args.reload:
        command.append("--reload")
    if args.workers > 1:
        command.extend(["--workers", str(args.workers)])
    _run(command)


def cmd_upgrade(args: argparse.Namespace) -> None:
    _run([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", args.revision])


def cmd_downgrade(args: argparse.Namespace) -> None:
    _run([sys.executable, "-m", "alembic", "-c", "alembic.ini", "downgrade", args.revision])


def cmd_revision(args: argparse.Namespace) -> None:
    command = [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        "alembic.ini",
        "revision",
        "-m",
        args.message,
    ]
    if args.autogenerate:
        command.append("--autogenerate")
    _run(command)


def cmd_seed(_: argparse.Namespace) -> None:
    from app.core.config import get_settings
    from app.db.init_db import ensure_default_admin, ensure_demo_users
    from app.db.session import SessionLocal

    settings = get_settings()
    with SessionLocal() as db:
        created_default = ensure_default_admin(db)
        demo_status = ensure_demo_users(db)
    if created_default:
        print("Default admin created")
    else:
        print("Default admin already exists")
    if settings.SEED_DEMO_USERS:
        print(
            "Demo admin:",
            "created" if demo_status["demo_admin"] else "already exists",
            f"(username={settings.DEMO_ADMIN_USERNAME}, email={settings.DEMO_ADMIN_EMAIL})",
        )
        print(
            "Demo vendor:",
            "created" if demo_status["demo_vendor"] else "already exists",
            f"(username={settings.DEMO_VENDOR_USERNAME}, email={settings.DEMO_VENDOR_EMAIL})",
        )


def cmd_check(_: argparse.Namespace) -> None:
    from sqlalchemy import text

    from app.core.config import get_settings
    from app.db.session import SessionLocal

    settings = get_settings()
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    print(f"Configuration and DB check passed for APP_ENV={settings.APP_ENV}")


def cmd_import_products(args: argparse.Namespace) -> None:
    from app.db.session import SessionLocal
    from app.services.product_import import fetch_dummyjson_products, import_products_from_records

    if args.from_dummyjson:
        records = fetch_dummyjson_products(limit=args.limit, skip=args.skip)
        source = "dummyjson"
    else:
        if not args.file:
            raise SystemExit("Provide --file when not using --from-dummyjson")
        file_path = Path(args.file).resolve()
        if not file_path.exists():
            raise SystemExit(f"File not found: {file_path}")

        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in {file_path}: {exc}") from exc
        if isinstance(payload, dict) and isinstance(payload.get("products"), list):
            records = payload["products"]
        elif isinstance(payload, list):
            records = payload
        else:
            raise SystemExit("JSON must be either a list of products or an object with a 'products' list")
        source = f"file:{file_path.name}"

    with SessionLocal() as db:
        report = import_products_from_records(
            db,
            records=records,
            source=source,
            update_existing=args.update_existing,
            default_category_name=args.default_category,
        )
        db.commit()

    print(json.dumps(report, indent=2))


def cmd_normalize_inr(args: argparse.Namespace) -> None:
    from decimal import Decimal

    from app.db.session import SessionLocal
    from app.models.cart import CartItem
    from app.models.order import Order, OrderItem, Payment
    from app.models.product import ProductVariant

    rate = Decimal(str(args.rate))

    def money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"))

    updated = {
        "variants": 0,
        "cart_items": 0,
        "order_items": 0,
        "orders": 0,
        "payments": 0,
    }

    with SessionLocal() as db:
        variants = db.query(ProductVariant).all()
        for variant in variants:
            if (variant.currency or "").upper() == "INR":
                continue
            variant.price = money(Decimal(variant.price) * rate)
            if variant.compare_at_price is not None:
                variant.compare_at_price = money(Decimal(variant.compare_at_price) * rate)
            variant.currency = "INR"
            db.add(variant)
            updated["variants"] += 1

        cart_items = db.query(CartItem).all()
        for item in cart_items:
            item.unit_price = money(Decimal(item.unit_price) * rate)
            db.add(item)
            updated["cart_items"] += 1

        order_items = db.query(OrderItem).all()
        for item in order_items:
            item.unit_price = money(Decimal(item.unit_price) * rate)
            item.tax_amount = money(Decimal(item.tax_amount) * rate)
            item.discount_amount = money(Decimal(item.discount_amount) * rate)
            item.line_total = money(Decimal(item.line_total) * rate)
            db.add(item)
            updated["order_items"] += 1

        orders = db.query(Order).all()
        for order in orders:
            order.subtotal = money(Decimal(order.subtotal) * rate)
            order.discount_total = money(Decimal(order.discount_total) * rate)
            order.tax_total = money(Decimal(order.tax_total) * rate)
            order.shipping_total = money(Decimal(order.shipping_total) * rate)
            order.grand_total = money(Decimal(order.grand_total) * rate)
            db.add(order)
            updated["orders"] += 1

        payments = db.query(Payment).all()
        for payment in payments:
            if (payment.currency or "").upper() != "INR":
                payment.amount = money(Decimal(payment.amount) * rate)
                payment.currency = "INR"
                db.add(payment)
                updated["payments"] += 1

        if args.dry_run:
            db.rollback()
            print(json.dumps({"dry_run": True, "rate": str(rate), "updated": updated}, indent=2))
            return

        db.commit()
        print(json.dumps({"dry_run": False, "rate": str(rate), "updated": updated}, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backend management commands")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run FastAPI server")
    run_parser.add_argument("--host", default="0.0.0.0")
    run_parser.add_argument("--port", type=int, default=8000)
    run_parser.add_argument("--reload", action="store_true")
    run_parser.add_argument("--workers", type=int, default=1)
    run_parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
    )
    run_parser.set_defaults(func=cmd_run)

    upgrade_parser = subparsers.add_parser("upgrade", help="Apply Alembic migrations")
    upgrade_parser.add_argument("revision", default="head", nargs="?")
    upgrade_parser.set_defaults(func=cmd_upgrade)

    downgrade_parser = subparsers.add_parser("downgrade", help="Rollback Alembic migrations")
    downgrade_parser.add_argument("revision", default="-1", nargs="?")
    downgrade_parser.set_defaults(func=cmd_downgrade)

    revision_parser = subparsers.add_parser("revision", help="Create Alembic revision")
    revision_parser.add_argument("-m", "--message", required=True)
    revision_parser.add_argument("--autogenerate", action="store_true")
    revision_parser.set_defaults(func=cmd_revision)

    seed_parser = subparsers.add_parser("seed", help="Seed default admin user")
    seed_parser.set_defaults(func=cmd_seed)

    check_parser = subparsers.add_parser("check", help="Validate config and DB connectivity")
    check_parser.set_defaults(func=cmd_check)

    import_parser = subparsers.add_parser("import-products", help="Import products from JSON file or DummyJSON")
    import_parser.add_argument("--file", help="Path to JSON file. Supports [{...}] or {\"products\": [...]}")
    import_parser.add_argument("--from-dummyjson", action="store_true", help="Fetch products from dummyjson.com")
    import_parser.add_argument("--limit", type=int, default=20)
    import_parser.add_argument("--skip", type=int, default=0)
    import_parser.add_argument("--default-category", default="Imported")
    import_parser.add_argument("--update-existing", action="store_true")
    import_parser.set_defaults(func=cmd_import_products)

    normalize_inr_parser = subparsers.add_parser(
        "normalize-inr",
        help="One-time conversion of existing DB monetary values to INR",
    )
    normalize_inr_parser.add_argument("--rate", type=float, default=83.0, help="USD to INR conversion rate")
    normalize_inr_parser.add_argument("--dry-run", action="store_true", help="Show conversion counts without commit")
    normalize_inr_parser.set_defaults(func=cmd_normalize_inr)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except subprocess.CalledProcessError as exc:
        # Bubble up child process exit code (uvicorn/alembic/etc.) without traceback noise.
        sys.exit(exc.returncode)
