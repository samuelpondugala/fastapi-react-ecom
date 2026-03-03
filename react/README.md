# Ecom React Frontend (Vite + JavaScript)

Frontend SPA for the FastAPI backend in `../fastapi`.

## Stack

- React 18
- React Router 6
- Vite 5
- JavaScript

## Frontend Capabilities

- Public storefront: home, catalog, product details
- Customer flows: login/register, cart, checkout, orders, profile
- Vendor/Admin product studio with bulk imports
- Admin operations: users, categories, products, coupons, order lookup
- Razorpay checkout popup integration (UPI/Card)
- Global toast notifications for success/error states
- Theme toggle (light/dark)

## Auth Model in UI

- Stores JWT token and profile in localStorage
- Calls `/auth/me` on app startup to hydrate session
- API requests include `credentials: 'include'`
- Supports backend Redis HttpOnly session cookie fallback
- Logout calls backend `/auth/logout` and clears local state

## Route Map

Public routes:

- `/`
- `/catalog`
- `/products/:productId`
- `/login`
- `/register`

Authenticated customer routes:

- `/cart`
- `/checkout`
- `/orders`
- `/orders/:orderId`
- `/profile`

Authenticated vendor/admin route:

- `/vendor/products`

Authenticated admin routes:

- `/admin`
- `/admin/users`
- `/admin/categories`
- `/admin/products`
- `/admin/coupons`
- `/admin/orders`

## Backend API Coverage

- `GET /health`, `GET /health/ready`
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
- `GET /users`, `GET /users/{id}`, `PATCH /users/me`
- `GET/POST/PATCH/DELETE /addresses/me...`
- `GET/POST/PATCH /categories...`
- `GET/POST/PATCH /products...`
- `POST /products/import/dummyjson`, `POST /products/import/json`
- `GET/POST/PATCH/DELETE /cart...`
- `POST /orders/checkout`, `GET /orders/me`, `GET /orders/{id}`
- `GET /orders/payment-gateways/free`
- `POST /orders/{id}/payment/quote`
- `POST /orders/{id}/payment/razorpay/order`
- `POST /orders/{id}/payment/razorpay/verify`
- `GET/POST /coupons`
- `GET /reviews/product/{product_id}`, `POST /reviews`

## Product Import UX

In `/vendor/products` and `/admin/products`:

- Import from DummyJSON
- Import from pasted JSON payload

DummyJSON constraints enforced in UI/backend:

- `limit` must be between `1` and `500`
- `skip` must be `>= 0`
- backend validation errors are normalized into readable toast messages

## Local Development

```bash
cd react
cp .env.example .env
npm install
npm run dev
```

Default env:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## Production Build

```bash
npm run build
npm run preview -- --host
```

Build output: `dist/`

## Deployment Notes

- Set `VITE_API_BASE_URL` to deployed backend `/api/v1` URL
- Add frontend domain to backend `CORS_ORIGINS`
- Ensure SPA rewrite fallback is configured (`/* -> /index.html`)
- For Render Static Site:
  - root directory: `react`
  - build command: `npm ci && npm run build`
  - publish directory: `dist`
