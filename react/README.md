# Ecom React Frontend (Vite + JavaScript)

This folder contains the customer storefront and admin UI for the FastAPI backend in `../fastapi`.

Stack:

- React 18
- React Router 6
- Vite 5
- Plain JavaScript (no TypeScript)

## Features

- Seamless routed UX across storefront and admin pages
- JWT auth with persistent session (`localStorage`)
- Customer flows:
  - Register/login
  - Browse catalog, filter/search products
  - Product details and reviews
  - Cart and 3-step checkout flow
  - Order history and order payment
  - Profile + addresses
  - Global top overlay toasts for success/error feedback
- Admin flows:
  - Dashboard metrics
  - Users list + inspect endpoint
  - Category management
  - Product creation + status updates
  - Coupon creation
  - Order lookup + payment action
- Payment flow supports:
  - UPI (`razorpay_upi`, `paytm_upi`)
  - Credit/Debit (`razorpay_card`)
  - EMI (`emi_plan`)
  - Pay Later (`pay_later`)
  - COD (`cod`)
  - Sandbox (`manual_free`, `mock_free`)
- Delivery policy in checkout: `< INR 1000` adds `INR 100`, else free
- Prices rendered in INR; timestamps rendered in IST
- For `razorpay_upi` / `razorpay_card`, frontend opens Razorpay Checkout popup and verifies signature through backend before marking order paid

## Route Map

Public routes:

- `/` Home
- `/catalog` Catalog listing + filters
- `/products/:productId` Product details + reviews
- `/login` Login
- `/register` Register

Authenticated customer routes:

- `/cart`
- `/checkout`
- `/orders`
- `/orders/:orderId`
- `/profile`

Authenticated vendor/admin route:

- `/vendor/products` (create products + import from DummyJSON/manual JSON)

Authenticated admin routes:

- `/admin`
- `/admin/users`
- `/admin/categories`
- `/admin/products`
- `/admin/coupons`
- `/admin/orders`

## API Coverage

The UI integrates these backend route groups:

- `GET /health`, `GET /health/ready`
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `GET /users`, `GET /users/{id}`, `PATCH /users/me`
- `GET/POST/PATCH/DELETE /addresses/me...`
- `GET/POST/PATCH /categories...`
- `GET/POST/PATCH /products...`
- `POST /products/import/dummyjson`, `POST /products/import/json`
- `GET/POST/PATCH/DELETE /cart...`
- `POST /orders/checkout`, `GET /orders/me`, `GET /orders/{id}`
- `GET /orders/payment-gateways/free`
- `POST /orders/{id}/payment/quote`
- `POST /orders/{id}/pay`
- `GET/POST /coupons`
- `GET /reviews/product/{product_id}`, `POST /reviews`

## Local Development

1. Install Node.js 20+ and npm.
2. From this folder:

```bash
cp .env.example .env
npm install
npm run dev
```

3. Open `http://localhost:5173`.
   If you open via `http://0.0.0.0:5173`, backend CORS must include `0.0.0.0` origin (already included in current backend defaults).

Default backend URL is:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

If backend runs on another host/port, update `.env` and restart Vite.

## Build for Production

```bash
npm run build
npm run preview -- --host
```

Output directory: `dist/`

## Auth and Admin Access

- Login/register uses `/auth/*` (login accepts email or username).
- Admin routes require user role `admin`.
- If you seed backend defaults, admin email is from `DEFAULT_ADMIN_EMAIL` in backend `.env`.

Demo credentials created by `python manage.py seed`:

- Admin: `ecomadmin` / `ecom@123admin`
- Vendor: `ecomvendor` / `ecom@123vendor`

Vendor users can use `/vendor/products` to add/import products.

## Deployment Notes

For full backend + frontend deployment on Render and AWS, see:

- `../DEPLOYMENT_GUIDE_RENDER_AWS.md`

Critical production settings:

- Set frontend env `VITE_API_BASE_URL` to your deployed backend `/api/v1` URL.
- Add frontend domain to backend `CORS_ORIGINS`.
- Ensure SPA fallback rewrite is enabled (`/* -> /index.html`) on static hosting.
