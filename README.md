
# Ecom Full Stack (FastAPI + React)

A production-oriented e-commerce project with:

- FastAPI backend (`fastapi/`)
- React + Vite frontend (`react/`)
- PostgreSQL-ready schema + Alembic migrations
- Redis-backed sessions/caching (optional, recommended in production)
- Razorpay payment integration (UPI/Card)
- CI checks for backend tests and frontend build

## Repository Structure

- `fastapi/` backend API, models, migrations, tests, Docker runtime
- `react/` frontend SPA (storefront + vendor/admin panels)
- `.github/workflows/ci.yml` CI pipeline
- `DEPLOYMENT_GUIDE_RENDER_AWS.md` deployment runbook
- `documentation.md` full technical documentation
- `presentation.md` presentation slide material
- `schema.drawio.png` schema diagram
- `react/architecture.drawio.png` architecture diagram

## Key Features

- Auth and roles: `customer`, `vendor`, `admin`
- Catalog: categories, products, variants, images
- Cart and checkout with delivery and coupons
- Payment flow via Razorpay:
  - create order
  - frontend checkout popup
  - backend signature verification
  - webhook reconciliation
- Product import:
  - from `dummyjson.com`
  - from pasted/manual JSON payload
- API protection:
  - JWT bearer auth
  - Redis-backed HttpOnly cookie session fallback
- Redis caching for high-read catalog endpoints

## Local Quick Start

## 1) Backend

```bash
cd fastapi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py upgrade head
python manage.py seed
python manage.py run --reload --host 0.0.0.0 --port 8000
```

Backend docs:

- Swagger: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 2) Frontend

```bash
cd react
cp .env.example .env
npm install
npm run dev
```

Frontend:

- App: `http://localhost:5173`
- Backend base URL: `VITE_API_BASE_URL=http://localhost:8000/api/v1`

## Demo Accounts

After `python manage.py seed`:

- Admin: `ecomadmin` / `ecom@123admin`
- Vendor: `ecomvendor` / `ecom@123vendor`

## Product Import Notes

- API endpoint: `POST /api/v1/products/import/dummyjson`
- `limit` is validated in range `1..500`
- For more than 500 products, import in batches with `skip`

Example CLI import:

```bash
cd fastapi
source .venv/bin/activate
python manage.py import-products --from-dummyjson --limit 500 --skip 0
python manage.py import-products --from-dummyjson --limit 500 --skip 500
```

## Payment Notes

Enabled payment providers:

- `razorpay_upi`
- `razorpay_card`

Primary endpoints:

- `POST /api/v1/orders/{id}/payment/razorpay/order`
- `POST /api/v1/orders/{id}/payment/razorpay/verify`
- `POST /api/v1/orders/payment/razorpay/webhook`

Legacy endpoint:

- `POST /api/v1/orders/{id}/pay` exists but intentionally returns an error for real gateways.

## Redis Session/Cookie Notes

When Redis is enabled:

- login sets HttpOnly session cookie (`SESSION_COOKIE_NAME`)
- auth dependency can resolve user from bearer token or session cookie
- logout clears session cookie and Redis session key
- category/product list/detail responses can be cached

## CI Pipeline

GitHub Actions workflow (`.github/workflows/ci.yml`) runs:

- FastAPI tests (`pytest -q`)
- React production build (`npm run build`)

## Deployment

- Full deployment guide: `DEPLOYMENT_GUIDE_RENDER_AWS.md`
- Backend service example: `https://fastapi-react-ecom.onrender.com`
- Razorpay webhook URL format:
  - `https://<your-backend-domain>/api/v1/orders/payment/razorpay/webhook`
