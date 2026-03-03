# Ecom Deployment Guide (Render + AWS)

Last updated: 2026-03-03

This guide is fully aligned with the current codebase and docs:

- `README.md`
- `fastapi/README.md`
- `react/README.md`
- `documentation.md`

It covers:

1. Backend deployment (FastAPI in `fastapi/`)
2. Frontend deployment (React in `react/`)
3. Redis-backed session/cookie + cache setup
4. Razorpay live payment setup (UPI/Card)

Repository layout assumed:

- `ecom/fastapi` backend
- `ecom/react` frontend

## 1) Current Production Architecture

1. React SPA served as static site
2. FastAPI backend served as Docker web service
3. Managed PostgreSQL database
4. Optional but recommended Redis service for:
   - server-side sessions
   - category/product API cache
5. Razorpay payment integration via backend create/verify/webhook endpoints
6. CI checks before deployment (`.github/workflows/ci.yml`)

Important implementation notes:

1. Payment providers enabled: `razorpay_upi`, `razorpay_card`
2. Legacy endpoint `POST /api/v1/orders/{order_id}/pay` is intentionally disabled for real gateways
3. DummyJSON import request limit is `1..500` (batch for larger imports)

## 2) Local Pre-Deployment Readiness

Run from repository root unless mentioned.

## 2.1 Backend setup check

```bash
cd fastapi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py check
python manage.py upgrade head
python manage.py seed
pytest -q
```

## 2.2 Frontend build check

```bash
cd react
cp .env.example .env
npm ci
npm run build
```

## 2.3 Optional local Docker check

```bash
cd fastapi
docker build -t ecom-api:local .
docker run --rm -p 8000:8000 \
  -e APP_ENV=dev \
  -e DATABASE_URL=sqlite:///./ecom.db \
  -e JWT_SECRET_KEY='local-secret' \
  -e DEFAULT_ADMIN_PASSWORD='local-password' \
  -e RUN_DB_MIGRATIONS=true \
  -e RUN_SEED=true \
  ecom-api:local
```

Verify:

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/health/ready
```

## 3) Environment Variable Plan (Canonical)

## 3.1 Backend required

```env
APP_ENV=production
DEBUG=false
ENABLE_DOCS=false

DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME

JWT_SECRET_KEY=YOUR_LONG_RANDOM_SECRET
DEFAULT_ADMIN_PASSWORD=YOUR_STRONG_ADMIN_PASSWORD

ALLOWED_HOSTS=api.example.com,service-name.onrender.com
CORS_ORIGINS=https://your-frontend-domain.com

UVICORN_WORKERS=2
RUN_DB_MIGRATIONS=true
RUN_SEED=false
AUTO_BOOTSTRAP_STAFF=true
SEED_DEMO_USERS=false
```

## 3.2 Redis sessions/cache (recommended)

```env
REDIS_ENABLED=true
REDIS_URL=redis://default:password@host:6379/0
REDIS_CONNECT_TIMEOUT_SECONDS=2.0
REDIS_SOCKET_TIMEOUT_SECONDS=2.0

SESSION_COOKIE_NAME=ecom_sid
SESSION_COOKIE_MAX_AGE_SECONDS=604800
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
SESSION_COOKIE_DOMAIN=
SESSION_REDIS_PREFIX=session:
SESSION_TTL_SECONDS=604800

CACHE_REDIS_PREFIX=cache:
CACHE_TTL_SECONDS=120
```

Session cookie guidance:

1. Same-site frontend/backend (common on Render subdomains):
   - `SESSION_COOKIE_SAMESITE=lax`
   - `SESSION_COOKIE_DOMAIN=` (empty)
2. Cross-site domains:
   - `SESSION_COOKIE_SAMESITE=none`
   - `SESSION_COOKIE_SECURE=true`
   - optionally `SESSION_COOKIE_DOMAIN=.example.com`

## 3.3 Razorpay

```env
RAZORPAY_KEY_ID=rzp_live_xxx
RAZORPAY_KEY_SECRET=xxx
RAZORPAY_WEBHOOK_SECRET=whsec_xxx
```

## 3.4 Frontend required

```env
VITE_API_BASE_URL=https://api.example.com/api/v1
```

## 3.5 Optional seed/demo controls

```env
DEFAULT_ADMIN_EMAIL=admin@example.com
SEED_DEMO_USERS=true
DEMO_ADMIN_USERNAME=ecomadmin
DEMO_ADMIN_EMAIL=ecomadmin@example.com
DEMO_ADMIN_PASSWORD=ecom@123admin
DEMO_VENDOR_USERNAME=ecomvendor
DEMO_VENDOR_EMAIL=ecomvendor@example.com
DEMO_VENDOR_PASSWORD=ecom@123vendor
```

## 4) Track A: Deploy to Render

## 4.1 Create managed services

1. Create Render PostgreSQL
2. Create Render Redis/Key-Value service (recommended)
3. Copy internal connection strings

## 4.2 Create backend web service

1. New -> Web Service
2. Connect repo
3. Root directory: `fastapi`
4. Runtime: `Docker`
5. Branch: deployment branch (`main` recommended)
6. Health check path: `/api/v1/health/ready`

No custom start command needed (Dockerfile handles `PORT` + workers).

## 4.3 Set backend environment (Render)

Set all variables from Section 3.

Minimum production set:

1. Core runtime + DB + auth
2. Host/CORS values
3. Razorpay keys + webhook secret
4. Redis block if using session/caching

Deploy and watch logs:

Expected startup sequence:

1. `python manage.py upgrade head` (if `RUN_DB_MIGRATIONS=true`)
2. `python manage.py seed-if-needed` (if `AUTO_BOOTSTRAP_STAFF=true`)
3. app starts with `python manage.py run --host 0.0.0.0 --port ${PORT}`

## 4.4 Verify backend

```bash
curl -s https://your-backend.onrender.com/api/v1/health
curl -s https://your-backend.onrender.com/api/v1/health/ready
```

Check login + profile:

1. `POST /api/v1/auth/login`
2. `GET /api/v1/auth/me`
3. `POST /api/v1/auth/logout`

## 4.5 Razorpay webhook on Render

Webhook URL:

- `https://<your-backend-domain>/api/v1/orders/payment/razorpay/webhook`

Set webhook events:

1. `payment.captured`
2. `order.paid`

Critical requirement:

- Razorpay webhook secret must exactly match `RAZORPAY_WEBHOOK_SECRET` env var.

Configure separately for Test mode and Live mode in Razorpay dashboard.

## 4.6 Deploy frontend on Render Static Site

1. New -> Static Site
2. Root directory: `react`
3. Build command: `npm ci && npm run build`
4. Publish directory: `dist`
5. Set env: `VITE_API_BASE_URL=https://your-backend-domain/api/v1`
6. Add SPA rewrite rule:
   - Source: `/*`
   - Destination: `/index.html`
   - Action: `Rewrite`

Verify routes including refresh:

- `/catalog`
- `/orders/:id`
- `/admin/*`

## 4.7 Render operations guidance

1. Keep `RUN_SEED=false` after initial setup
2. Keep `AUTO_BOOTSTRAP_STAFF=true` for safe first-deploy bootstrap behavior
3. Rollback using Render deployment history if needed

## 5) Track B: Deploy to AWS (App Runner + ECR + RDS)

## 5.1 Prerequisites

1. IAM permissions for ECR, App Runner, RDS, VPC, CloudWatch, Secrets Manager
2. AWS CLI configured
3. Docker installed

Set vars:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO=ecom-api
```

## 5.2 Build and push backend image

```bash
aws ecr create-repository --repository-name "$ECR_REPO" --region "$AWS_REGION"

aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

cd fastapi
docker build -t "$ECR_REPO:latest" .
docker tag "$ECR_REPO:latest" "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest"
```

## 5.3 Create data services

1. RDS PostgreSQL
2. (Recommended) ElastiCache Redis

Use private networking and security groups allowing only app-tier access.

## 5.4 Create App Runner service

1. Source: ECR image
2. Port: `8000`
3. Health check: `/api/v1/health/ready`
4. Attach VPC connector (for private RDS/Redis)

Set env vars from Section 3.

Recommended secrets via Secrets Manager:

1. `JWT_SECRET_KEY`
2. `DEFAULT_ADMIN_PASSWORD`
3. `DATABASE_URL`
4. `REDIS_URL`
5. `RAZORPAY_KEY_SECRET`
6. `RAZORPAY_WEBHOOK_SECRET`

## 5.5 Frontend on AWS

Option A: Amplify Hosting

1. Connect repo
2. App root: `react`
3. Build: `npm ci && npm run build`
4. Artifacts: `dist`
5. Env: `VITE_API_BASE_URL=https://api.example.com/api/v1`
6. SPA rewrite: `/<*> -> /index.html (200 rewrite)`

Option B: S3 + CloudFront

1. Build in `react`
2. Upload `dist/`
3. Configure CloudFront SPA fallback:
   - `403 -> /index.html (200)`
   - `404 -> /index.html (200)`
4. Invalidate cache after deploy

## 6) Payment Setup Checklist (Razorpay)

1. Generate API keys in dashboard
2. Set backend env vars (`RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`)
3. Create webhook to backend URL
4. Set webhook secret and mirror it in backend env
5. Verify flows in staging:
   - UPI success/failure
   - card success/failure
   - webhook callback processing

Razorpay links:

- Keys: `https://dashboard.razorpay.com/app/keys`
- Webhooks: `https://dashboard.razorpay.com/app/webhooks`
- API key docs: `https://razorpay.com/docs/payments/dashboard/account-settings/api-keys/`
- Webhook docs: `https://razorpay.com/docs/webhooks`

## 7) Post-Deployment Verification Checklist

1. `GET /api/v1/health` = 200
2. `GET /api/v1/health/ready` = 200
3. Register/login/me/logout flows work
4. Product list and category list load
5. DummyJSON import works with valid range (`limit <= 500`)
6. Cart -> checkout flow works
7. `GET /api/v1/orders/payment-gateways/free` returns Razorpay providers
8. `POST /api/v1/orders/{order_id}/payment/quote` works
9. `POST /api/v1/orders/{order_id}/payment/razorpay/order` works
10. `POST /api/v1/orders/{order_id}/payment/razorpay/verify` works
11. Webhook callback is accepted with valid signature
12. Frontend route refresh works without JS asset 404s
13. CORS errors absent in browser console
14. Session cookie behavior works as expected (if Redis enabled)

## 8) Common Failure Cases and Fixes

## 8.1 `Invalid host header`

Cause:

- backend `ALLOWED_HOSTS` missing deployed host/domain

Fix:

- set `ALLOWED_HOSTS` to include backend host(s)

## 8.2 White page on refresh + `index-*.js` 404

Cause:

- static host not configured for SPA rewrite or wrong publish dir/build root

Fix:

1. root `react`
2. build `npm ci && npm run build`
3. publish `dist`
4. rewrite `/* -> /index.html`
5. clear build/cache and redeploy

## 8.3 DummyJSON import 422

Cause:

1. request `limit` outside `1..500`
2. malformed payload

Fix:

- send valid `limit` and `skip`, batch large imports

## 8.4 Payment stays unpaid after successful checkout popup

Cause:

1. verify endpoint not called after success callback
2. webhook secret mismatch
3. webhook URL not reachable

Fix:

1. ensure frontend calls `POST /api/v1/orders/{order_id}/payment/razorpay/verify`
2. match `RAZORPAY_WEBHOOK_SECRET` exactly
3. verify public webhook endpoint accessibility

## 8.5 Cookie/session not persisting

Cause:

1. Redis disabled/unreachable
2. incorrect cookie same-site/domain setup
3. missing `allow_credentials` usage patterns across frontend/backend

Fix:

1. set `REDIS_ENABLED=true` and valid `REDIS_URL`
2. choose correct `SESSION_COOKIE_SAMESITE` and `SESSION_COOKIE_DOMAIN`
3. keep frontend requests with `credentials: 'include'`

## 8.6 DB connection refused

Cause:

- invalid `DATABASE_URL` / network rules

Fix:

1. validate credentials and host
2. check private networking/security groups
3. confirm DB service health

## 9) CI/CD Recommendation

Recommended pipeline order:

1. run backend tests (`pytest -q`)
2. run frontend build (`npm run build`)
3. build/push backend image
4. deploy backend with migrations
5. deploy frontend
6. run smoke checks (`/health`, `/health/ready`, login)

## 10) Official References

Render:

- https://render.com/docs/docker
- https://render.com/docs/web-services
- https://render.com/docs/static-sites
- https://render.com/docs/health-checks
- https://render.com/docs/environment-variables
- https://render.com/docs/postgresql-creating-connecting

AWS:

- https://docs.aws.amazon.com/apprunner/latest/dg/what-is-apprunner.html
- https://docs.aws.amazon.com/apprunner/latest/dg/service-source-image.html
- https://docs.aws.amazon.com/apprunner/latest/dg/manage-configure-healthcheck.html
- https://docs.aws.amazon.com/apprunner/latest/dg/network-vpc.html
- https://docs.aws.amazon.com/AmazonECR/latest/userguide/getting-started-cli.html
- https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html
- https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html
- https://docs.aws.amazon.com/amplify/latest/userguide/welcome.html
- https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html
