# Ecom Full Stack (FastAPI + React)

Repository structure:

- `fastapi/` Backend API (FastAPI, SQLAlchemy, Alembic, tests)
- `react/` Frontend UI (Vite + React + JavaScript)
- `schema.drawio` Database ER design
- `DEPLOYMENT_GUIDE_RENDER_AWS.md` Detailed deployment guide

## Quick Start (Local)

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
- Backend base URL (env): `VITE_API_BASE_URL=http://localhost:8000/api/v1`

## Admin Panel

Frontend admin routes:

- `/admin`
- `/admin/users`
- `/admin/categories`
- `/admin/products`
- `/admin/coupons`
- `/admin/orders`

You must login as an admin user to access these pages.

Seeded demo users after `python manage.py seed`:

- Admin username: `ecomadmin` (password: `ecom@123admin`)
- Vendor username: `ecomvendor` (password: `ecom@123vendor`)

Admin URL:

- `http://localhost:5173/admin`

Vendor product studio URL:

- `http://localhost:5173/vendor/products`

## Payment Behavior

- Free gateway options: `manual_free`, `mock_free`
- No mandatory paid payment provider account required
- Tax is applied only at payment step (`POST /orders/{id}/pay`)

## Dummy Data Import

Sample DummyJSON product payload file:

- `dummyjson_products_sample.json` (root)
- `fastapi/sample_dummyjson_products.json` (backend folder copy)

Import using CLI:

```bash
cd fastapi
source .venv/bin/activate
python manage.py import-products --from-dummyjson --limit 20 --skip 0
python manage.py import-products --file sample_dummyjson_products.json
```

Import from frontend:

- Login as `ecomadmin` or `ecomvendor`
- Open `/vendor/products` or `/admin/products`
- Use `Import from dummyjson.com` or paste JSON in the import textarea

## Documentation

- Backend setup and API details: `fastapi/README.md`
- Frontend setup and route coverage: `react/README.md`
- Cloud deployment (Render + AWS): `DEPLOYMENT_GUIDE_RENDER_AWS.md`
