# E-commerce FastAPI Backend

Production-oriented backend scaffold for your e-commerce project with:

- FastAPI application (`app/main.py`)
- SQLAlchemy 2.0 models matching `schema.drawio`
- Alembic migrations (`alembic/versions`)
- JWT auth (`/api/v1/auth`)
- CORS configured for React (`localhost:3000`, `localhost:5173`)
- Core e-commerce APIs: users, addresses, categories, products, cart, orders, coupons, reviews
- Production middleware: security headers, optional trusted hosts, gzip, and HTTPS redirect
- Test suite covering core success + failure scenarios (`tests/`)
- Real Razorpay payment flow (UPI/Card) with signature verification + webhook support
- Checkout supports coupon codes and delivery charge policy (free >= INR 1000, else INR 100)
- Companion React + Vite frontend in `../react` with storefront and admin panel

Detailed cloud deployment runbook (Render + AWS) is available at:

- [`../DEPLOYMENT_GUIDE_RENDER_AWS.md`](../DEPLOYMENT_GUIDE_RENDER_AWS.md)

## 1) Install

```bash
cd fastapi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2) Create DB schema

```bash
python manage.py upgrade head
python manage.py seed
```

`seed` creates the default admin from `.env`:

- `DEFAULT_ADMIN_EMAIL=admin@example.com`
- `DEFAULT_ADMIN_PASSWORD=Admin@1234`

`seed` also creates demo users (when `SEED_DEMO_USERS=true`):

- Admin: username `ecomadmin`, email `ecomadmin@example.com`, password `ecom@123admin`
- Vendor: username `ecomvendor`, email `ecomvendor@example.com`, password `ecom@123vendor`

Login supports email or username (email local-part), so `ecomadmin` works directly in login form.

## 3) Run API (dev)

```bash
python manage.py run --reload
```

Docs:

- Swagger: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Health endpoints:

- `GET /api/v1/health`
- `GET /api/v1/health/ready`

## 3.1) Run full stack locally (backend + React frontend)

Backend terminal:

```bash
cd fastapi
source .venv/bin/activate
python manage.py run --reload --host 0.0.0.0 --port 8000
```

Frontend terminal:

```bash
cd react
cp .env.example .env
npm install
npm run dev
```

Open:

- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

Frontend implementation details and route map are documented in:

- [`../react/README.md`](../react/README.md)

## 4) Run tests

```bash
pip install -r requirements-dev.txt
pytest
```

## 5) React integration

Base URL for frontend requests:

- `http://localhost:8000/api/v1`

Implemented UI routes:

- Public: `/`, `/catalog`, `/products/:productId`, `/login`, `/register`
- Authenticated: `/cart`, `/checkout`, `/orders`, `/orders/:orderId`, `/profile`
- Vendor/Admin: `/vendor/products` (create + import products)
- Admin: `/admin`, `/admin/users`, `/admin/categories`, `/admin/products`, `/admin/coupons`, `/admin/orders`

Example login flow:

```js
const baseURL = "http://localhost:8000/api/v1";

const loginRes = await fetch(`${baseURL}/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password }),
});
const { access_token } = await loginRes.json();

const productsRes = await fetch(`${baseURL}/products`, {
  headers: { Authorization: `Bearer ${access_token}` },
});
const products = await productsRes.json();
```

### Payment flow (Razorpay UPI/Card)

1. Create order from cart:

```http
POST /api/v1/orders/checkout
```

2. Optional quote before charging:

```http
POST /api/v1/orders/{order_id}/payment/quote
```

3. Create Razorpay checkout order:

```http
POST /api/v1/orders/{order_id}/payment/razorpay/order
```

4. Open Razorpay Checkout in frontend using returned `key_id` + `razorpay_order_id`.

5. Verify payment signature:

```http
POST /api/v1/orders/{order_id}/payment/razorpay/verify
```

Available providers:

- `razorpay_upi`
- `razorpay_card`

Real gateway credential placeholders in `.env`:

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`

Razorpay setup docs:

- API keys: `https://razorpay.com/docs/payments/dashboard/account-settings/api-keys/`
- Webhooks: `https://razorpay.com/docs/webhooks`

Razorpay end-to-end endpoints:

- `POST /api/v1/orders/{order_id}/payment/razorpay/order` (create Razorpay order)
- `POST /api/v1/orders/{order_id}/payment/razorpay/verify` (signature verification + mark paid)
- `POST /api/v1/orders/payment/razorpay/webhook` (server-side webhook callback)
- `POST /api/v1/orders/{order_id}/pay` is kept as a legacy endpoint and intentionally returns an error for real gateways

### Redis sessions + caching (recommended for production)

Enable Redis to support:

- HttpOnly browser session cookies (server-side session storage)
- Read-heavy API response caching (categories/products)

Required envs:

- `REDIS_ENABLED=true`
- `REDIS_URL=redis://...`
- `SESSION_COOKIE_SECURE=true` (for HTTPS)
- `SESSION_COOKIE_SAMESITE=none` (if frontend and backend are on different domains)
- `SESSION_COOKIE_DOMAIN` (optional cross-subdomain cookie scope)
- `SESSION_TTL_SECONDS` and `CACHE_TTL_SECONDS` for tuning

### Product import (DummyJSON + manual JSON)

API endpoints:

- `POST /api/v1/products/import/dummyjson`
- `POST /api/v1/products/import/json`

CLI options:

```bash
# import directly from dummyjson.com
python manage.py import-products --from-dummyjson --limit 20 --skip 0

# import from local JSON file
python manage.py import-products --file sample_dummyjson_products.json
```

Sample DummyJSON payload file in this repo:

- `sample_dummyjson_products.json` (inside `fastapi/`)
- `../dummyjson_products_sample.json` (root copy)

## 6) Production checklist

```bash
export APP_ENV=production
export DEBUG=false
export JWT_SECRET_KEY='replace-with-a-very-long-random-secret'
export DEFAULT_ADMIN_PASSWORD='replace-with-a-strong-admin-password'
python manage.py check
python manage.py upgrade head
python manage.py run --host 0.0.0.0 --port 8000 --workers 2
```

You should also set:

- `ALLOWED_HOSTS` to your domain(s), for example `api.example.com`
- `CORS_ORIGINS` to your frontend origins, for example `https://shop.example.com,https://admin.example.com`
- `ENABLE_HTTPS_REDIRECT=true` when TLS is terminated in front of app
- `SEED_DEMO_USERS=false` in production (avoid known demo credentials)
- Do not use angle brackets in shell exports (for example `<secret>`), use quoted string values directly

## 7) Docker (production-friendly)

```bash
docker build -t ecom-api .
docker run --rm -p 8000:8000 --env-file .env ecom-api
```

`docker-entrypoint.sh` automatically runs migrations by default (`RUN_DB_MIGRATIONS=true`).

It also bootstraps staff accounts by default when no admin/vendor exists (`AUTO_BOOTSTRAP_STAFF=true`), and supports explicit seed runs with `RUN_SEED=true`.

## 8) Common commands

```bash
python manage.py check
python manage.py revision -m "add new table" --autogenerate
python manage.py upgrade head
python manage.py downgrade -1
python manage.py normalize-inr --dry-run
python manage.py normalize-inr --rate 83
```

## API quick map

- `GET /api/v1/health`
- `GET /api/v1/health/ready`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `GET /api/v1/categories`
- `GET /api/v1/products`
- `POST /api/v1/products/import/dummyjson`
- `POST /api/v1/products/import/json`
- `GET /api/v1/cart/me`
- `POST /api/v1/cart/items`
- `POST /api/v1/orders/checkout`
- `GET /api/v1/orders/payment-gateways/free`
- `POST /api/v1/orders/{order_id}/payment/quote`
- `POST /api/v1/orders/{order_id}/payment/razorpay/order`
- `POST /api/v1/orders/{order_id}/payment/razorpay/verify`
- `POST /api/v1/orders/payment/razorpay/webhook`
- `GET /api/v1/orders/me`
- `POST /api/v1/reviews`
