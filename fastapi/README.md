# E-commerce FastAPI Backend

Backend service for the e-commerce platform with FastAPI + SQLAlchemy + Alembic.

## What This Backend Provides

- REST API under `/api/v1`
- SQLAlchemy 2.0 models and Alembic migrations
- Role-aware auth (`customer`, `vendor`, `admin`)
- JWT token auth with Redis-backed cookie session fallback
- Catalog, cart, checkout, orders, coupons, reviews
- Product import from DummyJSON and manual JSON payload
- Real Razorpay payment integration (UPI/Card)
- Optional Redis caching for read-heavy catalog APIs

Cloud deployment runbook:

- [`../DEPLOYMENT_GUIDE_RENDER_AWS.md`](../DEPLOYMENT_GUIDE_RENDER_AWS.md)

## 1) Installation

```bash
cd fastapi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2) Database Setup

```bash
python manage.py upgrade head
python manage.py seed
```

Default/demos from env:

- `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`
- `DEMO_ADMIN_*`, `DEMO_VENDOR_*` (when `SEED_DEMO_USERS=true`)

Login accepts email or username-style identity (email local-part / seeded display name).

## 3) Run API (Dev)

```bash
python manage.py run --reload
```

Docs and health:

- Swagger: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- Health: `GET /api/v1/health`
- Readiness: `GET /api/v1/health/ready`

## 4) Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## 5) Core API Areas

- Auth: `/auth/register`, `/auth/login`, `/auth/me`, `/auth/logout`
- Users: `/users`, `/users/{id}`, `/users/me`
- Addresses: `/addresses/me...`
- Categories: `/categories...`
- Products: `/products...`
- Cart: `/cart...`
- Orders: `/orders...`
- Coupons: `/coupons...`
- Reviews: `/reviews...`

## 6) Auth, Sessions, and Cookies

Authentication flow supports:

1. Bearer JWT token
2. Redis-backed session cookie fallback (`HttpOnly`)

Cookie/session behavior:

- Login creates JWT and tries to create Redis session
- If Redis session is created, API sets cookie (`SESSION_COOKIE_NAME`)
- `get_current_user` checks bearer token first, then session cookie
- Logout clears Redis session and deletes cookie

Relevant env vars:

- `REDIS_ENABLED`
- `REDIS_URL`
- `SESSION_COOKIE_NAME`
- `SESSION_COOKIE_MAX_AGE_SECONDS`
- `SESSION_COOKIE_SECURE`
- `SESSION_COOKIE_SAMESITE`
- `SESSION_COOKIE_DOMAIN`
- `SESSION_TTL_SECONDS`

## 7) Redis Caching

When `REDIS_ENABLED=true`, these use cache:

- `GET /categories`
- `GET /products`
- `GET /products/{product_id}`

Write/import operations invalidate affected cache namespaces.

Cache env vars:

- `CACHE_REDIS_PREFIX`
- `CACHE_TTL_SECONDS`

## 8) Payment Flow (Razorpay UPI/Card)

Enabled providers:

- `razorpay_upi`
- `razorpay_card`

Flow:

1. Checkout order from cart:

```http
POST /api/v1/orders/checkout
```

2. Optional quote:

```http
POST /api/v1/orders/{order_id}/payment/quote
```

3. Create Razorpay order:

```http
POST /api/v1/orders/{order_id}/payment/razorpay/order
```

4. Frontend opens Razorpay Checkout.

5. Verify signature and mark paid:

```http
POST /api/v1/orders/{order_id}/payment/razorpay/verify
```

6. Webhook reconciliation:

```http
POST /api/v1/orders/payment/razorpay/webhook
```

Legacy endpoint:

- `POST /api/v1/orders/{order_id}/pay` is intentionally disabled for real gateways and returns a validation error message.

Required env vars:

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`

Razorpay docs:

- API keys: `https://razorpay.com/docs/payments/dashboard/account-settings/api-keys/`
- Webhooks: `https://razorpay.com/docs/webhooks`

## 9) Product Import

Endpoints:

- `POST /api/v1/products/import/dummyjson`
- `POST /api/v1/products/import/json`

DummyJSON request constraints:

- `limit`: `1..500`
- `skip`: `>= 0`

CLI options:

```bash
# from dummyjson.com
python manage.py import-products --from-dummyjson --limit 500 --skip 0

# from local json file
python manage.py import-products --file sample_dummyjson_products.json
```

Sample files:

- `sample_dummyjson_products.json` (inside `fastapi/`)
- `../dummyjson_products_sample.json` (root)

## 10) Production Checklist

```bash
export APP_ENV=production
export DEBUG=false
export JWT_SECRET_KEY='replace-with-a-long-random-secret'
export DEFAULT_ADMIN_PASSWORD='replace-with-strong-password'
python manage.py check
python manage.py upgrade head
python manage.py run --host 0.0.0.0 --port 8000 --workers 2
```

Also set:

- `DATABASE_URL` (managed Postgres in production)
- `ALLOWED_HOSTS`
- `CORS_ORIGINS`
- `ENABLE_HTTPS_REDIRECT=true` (when applicable)
- `SEED_DEMO_USERS=false` (recommended in production)

Cookie guidance:

- Same-site frontend/backend: `SESSION_COOKIE_SAMESITE=lax`
- Cross-site frontend/backend: `SESSION_COOKIE_SAMESITE=none` and `SESSION_COOKIE_SECURE=true`

## 11) Docker

```bash
docker build -t ecom-api .
docker run --rm -p 8000:8000 --env-file .env ecom-api
```

Entrypoint behavior (`docker-entrypoint.sh`):

- `RUN_DB_MIGRATIONS=true` -> `upgrade head`
- `AUTO_BOOTSTRAP_STAFF=true` -> `seed-if-needed`
- `RUN_SEED=true` -> explicit full seed

Container command uses:

- `PORT` (default `8000`)
- `UVICORN_WORKERS` (default `2`)

## 12) Useful Commands

```bash
python manage.py check
python manage.py revision -m "add new table" --autogenerate
python manage.py upgrade head
python manage.py downgrade -1
python manage.py seed
python manage.py seed-if-needed
python manage.py import-products --from-dummyjson --limit 500 --skip 0
python manage.py normalize-inr --dry-run
python manage.py normalize-inr --rate 83
```
