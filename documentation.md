# Ecom Full-Stack Project Documentation

## 1. Project Overview

### 1.1 Project Name
Ecom Full Stack Commerce Platform

### 1.2 Purpose
This project delivers a production-oriented e-commerce platform with:
1. A FastAPI backend for authentication, catalog, cart, order, coupon, review, payment, and import workflows.
2. A React frontend for customer storefront, vendor product operations, and admin control panel.
3. Deployment-ready infrastructure and runbooks for Render and AWS.

### 1.3 Core Business Scope
1. Customer lifecycle: register, login, browse catalog, add to cart, checkout, pay, review products.
2. Staff lifecycle: admin and vendor can manage catalog and import products.
3. Operations lifecycle: migrations, seed/bootstrap users, CI validation, cloud deployment.

## 2. Technology Stack

### 2.1 Backend
1. FastAPI
2. SQLAlchemy 2.0 ORM
3. Alembic migrations
4. PostgreSQL (production) and SQLite (local/test default)
5. JWT authentication (`python-jose`) + password hashing (`passlib`)

### 2.2 Frontend
1. React 18
2. React Router 6
3. Vite 5
4. JavaScript (no TypeScript)

### 2.3 DevOps and Delivery
1. Dockerized backend runtime
2. Render and AWS deployment paths
3. GitHub Actions CI (`.github/workflows/ci.yml`)

## 3. Repository Structure

```text
ecom/
  fastapi/                       # Backend service
    app/
      api/                       # Routers + endpoint modules
      core/                      # Config, middleware, security
      db/                        # Base, session, init seed logic
      models/                    # SQLAlchemy domain models
      schemas/                   # Pydantic request/response schemas
      services/                  # Business logic services
    alembic/                     # Migration environment + revisions
    tests/                       # Backend test suite
    manage.py                    # Management CLI
    Dockerfile
    docker-entrypoint.sh
  react/                         # Frontend SPA
    src/
      pages/                     # Storefront, auth, profile, admin, vendor pages
      components/                # Shell, route guards, reusable UI
      context/                   # Auth context
      lib/                       # API client, formatters, toast bus
    vite.config.js
  .github/workflows/ci.yml       # CI pipeline
  DEPLOYMENT_GUIDE_RENDER_AWS.md # Cloud deployment runbook
  schema.drawio                  # Database ER diagram
  architecture.drawio            # System architecture diagram (this task)
```

## 4. High-Level Architecture

### 4.1 Diagram Artifacts
1. `schema.drawio`: entity relationship model and table-level links.
2. `architecture.drawio`: end-to-end system architecture, including client, frontend, backend layers, DB, integrations, and delivery pipeline.

### 4.2 Runtime Components
1. Client layer: customer, vendor, admin using browser.
2. Frontend layer: React SPA with route guards and API client.
3. Backend layer: FastAPI API + services + SQLAlchemy data layer.
4. Data layer: PostgreSQL/SQLite with Alembic-managed schema.
5. Integrations: DummyJSON import source, Razorpay API, Paytm credentials.
6. DevOps: GitHub Actions CI and cloud deploy paths.

### 4.3 Key Architectural Decisions
1. Service-oriented backend modules (`services/`) keep business rules out of route handlers.
2. JWT stateless auth enables horizontal API scaling.
3. Explicit role guards (`admin`, `vendor`, `customer`) enforce least privilege.
4. Migration-first schema strategy through Alembic ensures reproducible DB state.
5. Frontend route-level protection prevents unauthorized UI access.

## 5. Backend Architecture (FastAPI)

### 5.1 API Entry and Middleware
Primary entry: `fastapi/app/main.py`

Middleware stack:
1. CORS middleware with configurable origins.
2. GZip middleware (configurable).
3. HTTPS redirect middleware (configurable).
4. Trusted host middleware (optional via `ALLOWED_HOSTS`).
5. Custom security headers middleware (`X-Frame-Options`, CSP, etc.).

### 5.2 Routing Layout
API root prefix: `/api/v1`

Routers:
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

### 5.3 Security Model
1. Password hashing: PBKDF2 SHA-256 via `passlib`.
2. JWT token generation and decode via `python-jose`.
3. OAuth2 bearer token flow for protected routes.
4. Role-based dependencies:
   - `get_current_user`: authenticated active user
   - `get_admin_user`: admin-only
   - `get_staff_user`: admin or vendor

### 5.4 Configuration Model
Central settings source: `fastapi/app/core/config.py`

Major config groups:
1. App runtime: `APP_ENV`, `DEBUG`, `ENABLE_DOCS`, `API_V1_PREFIX`
2. Database: `DATABASE_URL`, pooling controls
3. Commerce defaults: currency, conversion, delivery thresholds
4. Security: JWT secret, expiry, host allowlist, CORS
5. Seeder controls: admin/demo accounts and passwords
6. Payment integration: Razorpay and Paytm credentials

Production guardrails:
1. Rejects insecure defaults in production (`DEBUG`, JWT secret, admin password).
2. Normalizes `ALLOWED_HOSTS` for URL/port/path mistakes.

## 6. Backend Domain Modules

### 6.1 Auth and User Management
1. Register customer accounts.
2. Login with email or username-style identity.
3. Username resolution supports email local-part and seeded display names.
4. Profile retrieval (`/auth/me`) and profile update (`/users/me`).
5. Admin-only user listing and user lookup.

### 6.2 Address Management
1. Customer can CRUD own addresses.
2. Default address logic unsets previous default automatically.

### 6.3 Catalog Management
1. Categories: list, create, update.
2. Products: list/filter/search, create, update, detail.
3. Product images and variants persisted with SKU uniqueness checks.

### 6.4 Product Import
1. Staff-only import endpoint from `https://dummyjson.com/products`.
2. Staff-only manual JSON import endpoint.
3. Import service normalizes source records and upserts products.
4. Import supports update-existing mode and category auto-creation.
5. Detailed upstream error handling for DummyJSON HTTP/network failures.

### 6.5 Cart and Checkout
1. Active cart per user (reactivation strategy when cart is converted).
2. Add/update/remove/clear cart items.
3. Checkout converts cart to order and creates inventory movement records.
4. Coupon discount applied at checkout if valid.
5. Delivery charge policy:
   - Subtotal `< 1000` INR: delivery charge `100`
   - Subtotal `>= 1000` INR: free delivery

### 6.6 Order and Payment
1. List my orders and get order details.
2. Payment quote endpoint calculates base + optional tax.
3. Free/sandbox payment flows (`manual_free`, `mock_free`, `cod`, etc.).
4. Razorpay order creation and signature verification flow.
5. Razorpay webhook endpoint validates signature and updates status.
6. Tax is intentionally applied at payment time, not at checkout.

### 6.7 Coupons and Reviews
1. Admin-only coupon creation and public/filtered coupon listing.
2. Product reviews with duplicate prevention (one review per user/product).
3. Verified purchase flag computed from order history.

## 7. Service Layer Responsibilities

### 7.1 `services/cart.py`
1. Active cart creation/reactivation and concurrent creation safeguards.
2. Cart item mutation logic and variant validation.

### 7.2 `services/order.py`
1. Checkout conversion from cart to order.
2. Coupon validation and discount calculation.
3. Shipping rule calculation.
4. Inventory movement writes for order reservation.

### 7.3 `services/payment.py`
1. Payment gateway registry and supported provider validation.
2. Payment quote and tax calculations.
3. Internal gateway processing and COD state handling.
4. Razorpay integration for order creation, signature verification, capture, webhook.

### 7.4 `services/product_import.py`
1. Remote fetch from DummyJSON.
2. Product normalization and INR conversion.
3. Upsert behavior for category/product/variant/images.

## 8. Database and Data Model

### 8.1 Core Entity Groups
1. Identity: `users`, `addresses`
2. Catalog: `categories`, `products`, `product_images`, `product_variants`
3. Cart: `carts`, `cart_items`
4. Order lifecycle: `orders`, `order_items`, `order_coupons`, `coupons`, `payments`, `shipments`
5. Inventory and quality: `inventory_movements`, `reviews`

### 8.2 Important Constraints
1. Unique user email.
2. Unique category slug.
3. Unique product slug.
4. Unique variant SKU.
5. Unique cart by user (`carts.user_id`).
6. Unique cart item per cart+variant.
7. Unique coupon code.
8. Unique review per user+product with rating check constraint (1-5).

### 8.3 Migration Strategy
1. Alembic environment uses app metadata from SQLAlchemy models.
2. `upgrade head` executed automatically in container entrypoint by default.
3. Initial schema migration defines all tables and indexes.

## 9. Seed, Bootstrap, and Operations

### 9.1 Startup Runtime Flow
`fastapi/docker-entrypoint.sh` execution order:
1. Run DB migrations when `RUN_DB_MIGRATIONS=true`.
2. Run staff bootstrap when `AUTO_BOOTSTRAP_STAFF=true`.
3. Run explicit seed when `RUN_SEED=true`.
4. Launch FastAPI with `manage.py run`.

### 9.2 Seed Behavior
1. `ensure_default_admin` creates or updates default admin credentials from env.
2. `ensure_demo_users` creates/updates demo admin and vendor when enabled.
3. `seed-if-needed` creates bootstrap staff only when no admin/vendor exists.

### 9.3 Management CLI (`manage.py`)
1. `run`
2. `check`
3. `upgrade`, `downgrade`, `revision`
4. `seed`, `seed-if-needed`
5. `import-products`
6. `normalize-inr`

## 10. Frontend Architecture (React)

### 10.1 App Composition
1. `main.jsx` wraps app in `BrowserRouter` and `AuthProvider`.
2. `App.jsx` declares public, authenticated, vendor, and admin routes.
3. `AppShell` handles global layout, nav, theme, and toast stack.
4. `AdminShell` provides side navigation for admin sections.
5. `ProtectedRoute` enforces auth and role checks.

### 10.2 State and Session
1. `AuthContext` stores JWT token and user profile in `localStorage`.
2. Auto-hydrates session on app load by calling `/auth/me`.
3. Exposes role flags (`isAdmin`, `isVendor`) for route/UI gating.

### 10.3 API Integration
1. Central API wrapper in `src/lib/api.js`.
2. Builds query strings, attaches bearer token, parses JSON/text.
3. Centralized error handling with UI toast notifications.
4. Uses `VITE_API_BASE_URL` for environment-specific backend routing.

### 10.4 Route Capabilities
1. Public: home, catalog, product detail, login, register.
2. Customer: cart, checkout, orders, order detail, profile.
3. Vendor/Admin: product studio and bulk import.
4. Admin: dashboard, users, categories, products, coupons, orders.

### 10.5 UX Utilities
1. Currency/time formatting uses INR and IST display conventions.
2. Toast bus provides global feedback for API operations.
3. Theme toggle persists in local storage.

## 11. API Capability Map

| Domain | Key Endpoints |
|---|---|
| Health | `GET /health`, `GET /health/ready` |
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` |
| Users | `GET /users`, `GET /users/{id}`, `PATCH /users/me` |
| Addresses | `GET/POST/PATCH/DELETE /addresses/me...` |
| Categories | `GET/POST/PATCH /categories...` |
| Products | `GET/POST/PATCH /products...` |
| Import | `POST /products/import/dummyjson`, `POST /products/import/json` |
| Cart | `GET /cart/me`, `POST/PATCH/DELETE /cart/items...`, `DELETE /cart/clear` |
| Orders | `POST /orders/checkout`, `GET /orders/me`, `GET /orders/{id}` |
| Payments | `GET /orders/payment-gateways/free`, `POST /orders/{id}/payment/quote`, `POST /orders/{id}/pay`, Razorpay create/verify/webhook |
| Coupons | `GET /coupons`, `POST /coupons` |
| Reviews | `GET /reviews/product/{product_id}`, `POST /reviews` |

## 12. Testing Strategy

### 12.1 Backend Test Organization
1. `test_auth.py`: registration, login, identity validation.
2. `test_users.py`: user permissions and profile behavior.
3. `test_catalog.py`: category/product authorization and validation.
4. `test_cart_orders.py`: cart lifecycle, checkout, payment behavior.
5. `test_reviews_coupons_addresses.py`: review/coupon/address constraints.
6. `test_product_import.py`: import authorization and import behavior.
7. `test_production_readiness.py`: middleware headers and production setting guards.

### 12.2 CI Pipeline
GitHub Actions workflow (`.github/workflows/ci.yml`):
1. FastAPI job:
   - Python 3.12
   - install `requirements-dev.txt`
   - run `pytest -q`
2. React job:
   - Node 20
   - `npm ci`
   - `npm run build`

## 13. Deployment and Infrastructure

### 13.1 Backend Container
1. Base image: `python:3.12-slim`
2. Includes `ca-certificates` for outbound HTTPS calls.
3. Runs as non-root user (`app`).
4. Entrypoint handles migrations and optional seed/bootstrap.

### 13.2 Render Deployment
1. Backend: Render Web Service (Docker root `fastapi`).
2. Frontend: Render Static Site (root `react`, publish `dist`, SPA rewrite).
3. Managed Postgres recommended for production.

### 13.3 AWS Deployment (Alternative)
1. Backend image to ECR.
2. Deploy via App Runner.
3. Persist data in RDS PostgreSQL.

### 13.4 Critical Environment Variables

| Area | Variables |
|---|---|
| Runtime | `APP_ENV`, `DEBUG`, `ENABLE_DOCS`, `UVICORN_WORKERS` |
| DB | `DATABASE_URL`, `RUN_DB_MIGRATIONS` |
| Auth/Security | `JWT_SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ORIGINS`, `ENABLE_HTTPS_REDIRECT` |
| Seed/Bootstrap | `AUTO_BOOTSTRAP_STAFF`, `RUN_SEED`, `SEED_DEMO_USERS`, `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_PASSWORD`, `DEMO_*` |
| Frontend | `VITE_API_BASE_URL` |
| Payments | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `PAYTM_MERCHANT_ID`, `PAYTM_MERCHANT_KEY` |

## 14. Security and Reliability Notes

1. JWT secret and admin credentials must be rotated for production.
2. `ALLOWED_HOSTS` and `CORS_ORIGINS` must be explicitly set per deployed domains.
3. Security middleware sets baseline protection headers.
4. Readiness endpoint verifies DB connectivity (`SELECT 1`).
5. Transactional migration and startup sequence reduce deployment drift risk.

## 15. End-to-End Functional Walkthrough (Presentation Flow)

### 15.1 Demo Storyline
1. Start at home/catalog and explain customer browsing flow.
2. Register or login as customer and add products to cart.
3. Checkout to create order and show delivery/coupon calculations.
4. Pay order using free gateway or Razorpay flow.
5. Switch to admin/vendor and show product import from DummyJSON.
6. Show admin dashboards for users, categories, products, coupons, and orders.

### 15.2 Key Talking Points for Presentation
1. Clear separation of concerns: routes vs services vs models.
2. Production readiness: Docker, migrations, env-validated config.
3. Role-based multi-tenant style UI/API controls.
4. Real payment gateway wiring with sandbox-safe fallbacks.
5. CI validation gates for backend and frontend before deployment.

## 16. Current Strengths and Future Enhancements

### 16.1 Strengths
1. Full-stack coverage from auth to payments.
2. Strong operational tooling (`manage.py`, migration automation, deployment runbook).
3. Good test coverage for critical business paths.
4. Extensible service layer for adding new providers and workflows.

### 16.2 Suggested Next Enhancements
1. Add frontend automated tests (unit/e2e).
2. Add API rate limiting and structured audit logs.
3. Add observability stack (traces/metrics dashboards).
4. Add background jobs for asynchronous email and fulfillment workflows.
5. Add advanced inventory controls and stock reservation expiry.

## 17. Quick Command Reference

### 17.1 Backend
```bash
cd fastapi
python manage.py check
python manage.py upgrade head
python manage.py seed
python manage.py run --host 0.0.0.0 --port 8000 --workers 2
python manage.py import-products --from-dummyjson --limit 20 --skip 0
```

### 17.2 Frontend
```bash
cd react
npm ci
npm run dev
npm run build
```

### 17.3 CI Validation
```bash
# backend checks
cd fastapi && pytest -q

# frontend build check
cd react && npm run build
```

---

## Appendix A: Diagram Files
1. `architecture.drawio` for full system architecture.
2. `schema.drawio` for detailed relational schema.

## Appendix B: Primary Documentation Files
1. `README.md` (repo overview)
2. `fastapi/README.md` (backend details)
3. `react/README.md` (frontend details)
4. `DEPLOYMENT_GUIDE_RENDER_AWS.md` (deployment runbook)
