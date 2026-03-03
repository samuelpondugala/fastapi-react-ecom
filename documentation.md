# Ecom Full-Stack Technical Documentation

## 1) Project Summary

Ecom is a full-stack e-commerce system built with FastAPI (backend) and React/Vite (frontend).

It supports:

1. Customer storefront and checkout journeys
2. Vendor/admin catalog operations
3. Real Razorpay payment processing (UPI/Card)
4. Redis-backed sessions/cookies and read caching
5. Dockerized deployment + CI validation

## 2) Current Architecture

## 2.1 Runtime Components

1. Browser client (customer/vendor/admin)
2. React SPA (`react/`)
3. FastAPI API (`fastapi/app/main.py`) at `/api/v1`
4. SQLAlchemy ORM + database (PostgreSQL in production, SQLite local/test)
5. Optional Redis for sessions and cache
6. External APIs:
   - DummyJSON product source
   - Razorpay payments

## 2.2 Diagram Assets in Repository

1. `schema.drawio.png` (schema view)
2. `react/architecture.drawio.png` (system architecture view)

## 3) Repository Layout

```text
ecom/
  fastapi/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
    alembic/
    tests/
    manage.py
    Dockerfile
    docker-entrypoint.sh
  react/
    src/
      components/
      context/
      lib/
      pages/
  .github/workflows/ci.yml
  DEPLOYMENT_GUIDE_RENDER_AWS.md
  README.md
  documentation.md
  presentation.md
```

## 4) Backend Design (FastAPI)

## 4.1 API and Middleware

Entry point: `fastapi/app/main.py`

Middleware stack:

1. CORS (`allow_credentials=True`)
2. GZip (optional)
3. HTTPS redirect (optional)
4. Trusted host (optional)
5. Security headers middleware

## 4.2 Route Modules

Mounted in `fastapi/app/api/router.py`:

1. `health`
2. `auth`
3. `users`
4. `addresses`
5. `categories`
6. `products`
7. `cart`
8. `orders`
9. `coupons`
10. `reviews`

## 4.3 Auth + Session Model

Implemented in:

- `fastapi/app/api/v1/endpoints/auth.py`
- `fastapi/app/api/deps.py`
- `fastapi/app/services/session.py`
- `fastapi/app/core/redis.py`

Behavior:

1. Login always returns JWT access token.
2. If Redis is enabled and available, login also writes a server-side session and sets an HttpOnly cookie.
3. Protected routes accept either:
   - valid bearer JWT, or
   - valid Redis session cookie.
4. Logout deletes Redis session and clears cookie.

## 4.4 Redis Cache Layer

Implemented in:

- `fastapi/app/services/cache.py`
- category/product endpoints

Current cache coverage:

1. `GET /categories`
2. `GET /products`
3. `GET /products/{id}`

Cache invalidated on create/update/import operations.

## 4.5 Product Import

Implemented in:

- `fastapi/app/services/product_import.py`
- `fastapi/app/schemas/importer.py`
- `fastapi/app/api/v1/endpoints/products.py`

Capabilities:

1. Import from `dummyjson.com`
2. Import from manual JSON payload
3. Upsert with `update_existing`
4. Category auto-creation
5. INR normalization for imported prices

Validation constraints:

- DummyJSON import `limit` is `1..500`
- `skip >= 0`

## 4.6 Payment Integration (Razorpay Only)

Implemented in:

- `fastapi/app/services/payment.py`
- `fastapi/app/api/v1/endpoints/orders.py`
- `fastapi/app/schemas/payment.py`

Enabled providers:

1. `razorpay_upi`
2. `razorpay_card`

Flow:

1. Checkout creates internal order
2. Optional quote endpoint calculates tax/total
3. Backend creates Razorpay order (`/payment/razorpay/order`)
4. Frontend opens Razorpay checkout popup
5. Backend verifies signature (`/payment/razorpay/verify`)
6. Webhook endpoint updates state asynchronously (`/payment/razorpay/webhook`)

Important behavior:

- Legacy endpoint `/orders/{id}/pay` exists but intentionally returns an error for real gateways.

## 5) Frontend Design (React)

## 5.1 App Structure

Key files:

1. `src/App.jsx` route map
2. `src/components/AppShell.jsx` shell, nav, toasts, theme toggle
3. `src/context/AuthContext.jsx` auth/session state
4. `src/lib/api.js` centralized API client
5. `src/pages/*` customer/vendor/admin pages

## 5.2 Frontend Auth Behavior

1. Stores token/user in localStorage
2. Calls `/auth/me` on startup
3. Includes `credentials: 'include'` in fetch calls
4. Supports Redis cookie session fallback transparently
5. Calls `/auth/logout` for backend session cleanup

## 5.3 Product Import UI

In `AdminProductsPage`/`VendorProductsPage`:

1. DummyJSON import form
2. Manual JSON import textarea
3. UI validation for limit/skip
4. Robust error normalization for FastAPI 422 response shapes

## 5.4 Payment UI

In `OrderDetailPage`:

1. provider selection limited to `razorpay_upi` and `razorpay_card`
2. Razorpay checkout script loader
3. verify endpoint call after successful payment callback

## 6) Data Model Summary

Main entities:

1. Users and addresses
2. Categories, products, variants, images
3. Carts and cart items
4. Orders and order items
5. Coupons
6. Payments
7. Reviews
8. Inventory movements

Schema evolution is managed by Alembic migrations (`fastapi/alembic`).

## 7) Configuration and Environment Variables

## 7.1 Backend Core

- `APP_ENV`, `DEBUG`, `ENABLE_DOCS`
- `DATABASE_URL`, SQL pool settings
- `CORS_ORIGINS`, `ALLOWED_HOSTS`
- `ENABLE_HTTPS_REDIRECT`, `ENABLE_GZIP`
- `JWT_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`

## 7.2 Redis + Session + Cache

- `REDIS_ENABLED`
- `REDIS_URL`
- `REDIS_CONNECT_TIMEOUT_SECONDS`
- `REDIS_SOCKET_TIMEOUT_SECONDS`
- `SESSION_COOKIE_NAME`
- `SESSION_COOKIE_MAX_AGE_SECONDS`
- `SESSION_COOKIE_SECURE`
- `SESSION_COOKIE_SAMESITE`
- `SESSION_COOKIE_DOMAIN`
- `SESSION_REDIS_PREFIX`
- `SESSION_TTL_SECONDS`
- `CACHE_REDIS_PREFIX`
- `CACHE_TTL_SECONDS`

## 7.3 Seed and Bootstrap

- `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`
- `SEED_DEMO_USERS`
- `DEMO_ADMIN_*`, `DEMO_VENDOR_*`
- Docker entrypoint runtime flags:
  - `RUN_DB_MIGRATIONS`
  - `AUTO_BOOTSTRAP_STAFF`
  - `RUN_SEED`

## 7.4 Payment

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`

## 7.5 Frontend

- `VITE_API_BASE_URL`

## 8) API Map (Important Endpoints)

## 8.1 Auth and User

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `GET /api/v1/users`
- `GET /api/v1/users/{id}`
- `PATCH /api/v1/users/me`

## 8.2 Catalog and Import

- `GET /api/v1/categories`
- `POST /api/v1/categories`
- `PATCH /api/v1/categories/{id}`
- `GET /api/v1/products`
- `GET /api/v1/products/{id}`
- `POST /api/v1/products`
- `PATCH /api/v1/products/{id}`
- `POST /api/v1/products/import/dummyjson`
- `POST /api/v1/products/import/json`

## 8.3 Cart, Orders, Payments

- `GET /api/v1/cart/me`
- `POST /api/v1/cart/items`
- `PATCH /api/v1/cart/items/{id}`
- `DELETE /api/v1/cart/items/{id}`
- `DELETE /api/v1/cart/clear`
- `POST /api/v1/orders/checkout`
- `GET /api/v1/orders/me`
- `GET /api/v1/orders/{id}`
- `GET /api/v1/orders/payment-gateways/free`
- `POST /api/v1/orders/{id}/payment/quote`
- `POST /api/v1/orders/{id}/payment/razorpay/order`
- `POST /api/v1/orders/{id}/payment/razorpay/verify`
- `POST /api/v1/orders/payment/razorpay/webhook`

## 8.4 Coupons, Reviews, Health

- `GET /api/v1/coupons`
- `POST /api/v1/coupons`
- `GET /api/v1/reviews/product/{product_id}`
- `POST /api/v1/reviews`
- `GET /api/v1/health`
- `GET /api/v1/health/ready`

## 9) CI/CD and Deployment

## 9.1 CI Workflow

File: `.github/workflows/ci.yml`

Jobs:

1. FastAPI tests (`pytest -q`)
2. React build (`npm run build`)

## 9.2 Docker Runtime

- Dockerfile uses `python:3.12-slim`
- non-root runtime user
- startup command:
  - `python manage.py run --host 0.0.0.0 --port ${PORT:-8000} --workers ${UVICORN_WORKERS:-2}`

## 9.3 Deployment References

- `DEPLOYMENT_GUIDE_RENDER_AWS.md`
- Render backend webhook example:
  - `https://fastapi-react-ecom.onrender.com/api/v1/orders/payment/razorpay/webhook`

## 10) Operations Playbook

## 10.1 Backend Local Commands

```bash
cd fastapi
source .venv/bin/activate
python manage.py check
python manage.py upgrade head
python manage.py seed
python manage.py run --reload --host 0.0.0.0 --port 8000
```

## 10.2 Import in Batches

```bash
python manage.py import-products --from-dummyjson --limit 500 --skip 0
python manage.py import-products --from-dummyjson --limit 500 --skip 500
```

## 10.3 Frontend Local Commands

```bash
cd react
npm ci
npm run dev
npm run build
```

## 11) Known Constraints and Next Steps

Current constraints:

1. `/orders/{id}/pay` is intentionally disabled for live gateway flow.
2. Payment support is limited to Razorpay UPI/Card providers.
3. Automated frontend tests are not yet part of CI.

Recommended next enhancements:

1. Add React unit/e2e tests.
2. Add rate limiting and structured audit logs.
3. Add observability (metrics, tracing, dashboards).
4. Add async jobs for notifications and fulfillment.

