# Ecom Backend Deployment Guide (Render + AWS)

Last updated: 2026-02-25

This guide explains, stage-by-stage, how to deploy the backend in `fastapi/` to:

1. Render (fastest path)
2. AWS App Runner + ECR + RDS PostgreSQL (AWS-managed path)

It is written for this repository layout:

- `ecom/fastapi/` -> FastAPI backend
- `ecom/react/` -> frontend app

## Stage 0: Understand the production architecture

For both platforms, the production architecture is:

1. React SPA frontend (`ecom/react`) served from static hosting
2. Containerized FastAPI app (`ecom/fastapi`) for API
3. Managed PostgreSQL database (not SQLite)
4. Environment variables for secrets/config
5. Health checks (`/api/v1/health/ready`)
6. HTTPS endpoints for frontend and backend domains
7. Built-in free payment gateways (`manual_free`, `mock_free`) with tax applied at payment stage

Important notes:

- Do not use SQLite in production.
- Do not keep default secrets in production.
- Do not open `/docs` publicly unless you intentionally want it accessible.
- Taxes are applied only when calling `POST /api/v1/orders/{order_id}/pay`.

## Stage 1: Local readiness checklist

Run these from `ecom/fastapi`.

### 1.1 Create and activate virtualenv

```bash
python -m venv .venv
source .venv/bin/activate
```

### 1.2 Install dependencies

```bash
pip install -r requirements-dev.txt
```

### 1.3 Verify tests pass

```bash
pytest
```

### 1.4 Verify app config and DB migration locally

```bash
python manage.py check
python manage.py upgrade head
python manage.py seed
```

### 1.5 Verify frontend build locally

Run from `ecom/react`:

```bash
npm ci
npm run build
```

## Stage 2: Production environment variable plan

You will set these in Render/AWS:

```env
APP_ENV=production
DEBUG=false
ENABLE_DOCS=false

# Use managed Postgres URL (Render/AWS RDS)
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME

# Must be changed from defaults
JWT_SECRET_KEY=YOUR_LONG_RANDOM_SECRET
DEFAULT_ADMIN_PASSWORD=YOUR_STRONG_ADMIN_PASSWORD

# Your domains
ALLOWED_HOSTS=api.example.com,service-name.onrender.com
CORS_ORIGINS=https://your-frontend-domain.com

# Runtime tuning
UVICORN_WORKERS=2
RUN_DB_MIGRATIONS=true
RUN_SEED=false
SEED_DEMO_USERS=false

# Frontend build env (React)
VITE_API_BASE_URL=https://api.example.com/api/v1
```

Generate secure values:

```bash
python - <<'PY'
import secrets
print('JWT_SECRET_KEY=' + secrets.token_urlsafe(64))
print('DEFAULT_ADMIN_PASSWORD=' + secrets.token_urlsafe(24))
PY
```

## Stage 3: Container build verification

Before cloud deploy, verify Docker image locally.

### 3.1 Build image

From `ecom/fastapi`:

```bash
docker build -t ecom-api:local .
```

### 3.2 Run image locally

```bash
docker run --rm -p 8000:8000 \
  -e APP_ENV=dev \
  -e DEBUG=false \
  -e DATABASE_URL=sqlite:///./ecom.db \
  -e JWT_SECRET_KEY='local-secret-not-for-prod' \
  -e DEFAULT_ADMIN_PASSWORD='local-password' \
  -e RUN_DB_MIGRATIONS=true \
  -e RUN_SEED=true \
  ecom-api:local
```

### 3.3 Verify

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/health/ready
```

---

## Track A: Deploy to Render (recommended fastest)

## Stage R1: Create PostgreSQL on Render

1. Open Render dashboard.
2. Create `PostgreSQL` service.
3. Pick region closest to users.
4. Save:
   - Internal Database URL
   - External Database URL (optional)

Use internal URL for backend service.

## Stage R2: Create backend Web Service

1. Click `New` -> `Web Service`.
2. Connect your Git repository.
3. Root directory: `fastapi`
4. Runtime: `Docker`
5. Branch: your deployment branch (`main` recommended)

No custom start command is required because Docker now supports `PORT` and `UVICORN_WORKERS` env vars.

## Stage R3: Configure environment variables

In Render service `Environment` section, set:

```env
APP_ENV=production
DEBUG=false
ENABLE_DOCS=false
DATABASE_URL=postgresql+psycopg://...  # from Render Postgres Internal URL
JWT_SECRET_KEY=...
DEFAULT_ADMIN_PASSWORD=...
ALLOWED_HOSTS=your-service.onrender.com,api.example.com
CORS_ORIGINS=https://your-frontend-domain.com
UVICORN_WORKERS=2
RUN_DB_MIGRATIONS=true
RUN_SEED=false
```

Optional:

```env
ENABLE_HTTPS_REDIRECT=true
```

## Stage R4: Health check and deploy

1. Set health check path:

```text
/api/v1/health/ready
```

2. Trigger deploy.
3. Watch logs until startup completes.

Expected startup behavior:

1. `docker-entrypoint.sh` runs migrations when `RUN_DB_MIGRATIONS=true`
2. app starts with `python manage.py run ...`
3. health check becomes healthy

## Stage R5: Verify deployment

1. Open service URL root:

```text
https://your-service.onrender.com/
```

2. Verify API:

```bash
curl -s https://your-service.onrender.com/api/v1/health
curl -s https://your-service.onrender.com/api/v1/health/ready
```

3. (If docs enabled) verify Swagger at `/docs`.

## Stage R6: Connect React frontend

Set frontend env:

```env
VITE_API_BASE_URL=https://your-service.onrender.com/api/v1
```

Redeploy frontend.

## Stage R7: Add custom domain

1. In Render service -> `Settings` -> `Custom Domains`.
2. Add `api.example.com`.
3. Update DNS records as instructed by Render.
4. Wait for SSL issuance.
5. Update `ALLOWED_HOSTS` and frontend API base URL to custom domain.

## Stage R8: Render production operations

1. Keep `RUN_SEED=false` after first setup.
2. Keep at least one instance running.
3. Use Render logs + metrics for monitoring.
4. If deploy fails, rollback to previous deploy from Render dashboard.

## Stage R9: Deploy frontend on Render Static Site

Use this for the `ecom/react` Vite app.

1. In Render, create `Static Site`.
2. Connect the same repository.
3. Configure:
   - Root directory: `react`
   - Build command: `npm ci && npm run build`
   - Publish directory: `dist`
4. Add environment variable:

```env
VITE_API_BASE_URL=https://your-api-domain.com/api/v1
```

5. Add SPA rewrite rule:
   - Source: `/*`
   - Destination: `/index.html`
   - Action: `Rewrite`
6. Deploy and verify:
   - `https://your-frontend.onrender.com/`
   - Login/register
   - Catalog loading
   - Checkout and payment pages
   - Admin pages (`/admin/*`) render with routing refresh support

---

## Track B: Deploy to AWS (App Runner + ECR + RDS)

This path keeps operations simple while staying fully in AWS.

## Stage A1: AWS prerequisites

1. AWS account and IAM user/role with permissions for:
   - ECR
   - App Runner
   - RDS
   - VPC
   - CloudWatch Logs
   - Secrets Manager
2. AWS CLI configured:

```bash
aws configure
```

3. Docker installed locally.

Set shell variables:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO=ecom-api
```

## Stage A2: Create ECR repository

```bash
aws ecr create-repository \
  --repository-name "$ECR_REPO" \
  --region "$AWS_REGION"
```

## Stage A3: Build and push Docker image to ECR

From `ecom/fastapi`:

```bash
aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -t "$ECR_REPO:latest" .

docker tag "$ECR_REPO:latest" \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest"

docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest"
```

## Stage A4: Create RDS PostgreSQL

Use AWS Console (recommended for first deployment):

1. Go to RDS -> Create database.
2. Engine: PostgreSQL.
3. Template: Production (or Dev/Test for cheaper setup).
4. Place DB in private subnets.
5. Create security group `rds-sg` allowing inbound `5432` only from App Runner connector SG.
6. Save endpoint, username, db name, password.

Construct SQLAlchemy URL:

```text
postgresql+psycopg://DB_USER:DB_PASSWORD@RDS_ENDPOINT:5432/DB_NAME
```

## Stage A5: Create secrets in Secrets Manager

Store sensitive values:

```bash
aws secretsmanager create-secret \
  --name ecom/prod/jwt_secret \
  --secret-string "$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(64))
PY
)" \
  --region "$AWS_REGION"

aws secretsmanager create-secret \
  --name ecom/prod/admin_password \
  --secret-string "$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)" \
  --region "$AWS_REGION"
```

You can also store `DATABASE_URL` as a secret.

## Stage A6: Create App Runner service

1. Open App Runner -> `Create service`.
2. Source: `Container registry` -> `Amazon ECR`.
3. Select image: `$ECR_REPO:latest`.
4. Deployment trigger: manual first, then automatic if desired.
5. Service settings:
   - Port: `8000`
   - Health check path: `/api/v1/health/ready`
   - CPU/Memory: start with 1 vCPU / 2 GB

## Stage A7: Configure App Runner environment

Set plain env vars:

```env
APP_ENV=production
DEBUG=false
ENABLE_DOCS=false
DATABASE_URL=postgresql+psycopg://...
ALLOWED_HOSTS=your-apprunner-domain.awsapprunner.com,api.example.com
CORS_ORIGINS=https://your-frontend-domain.com
UVICORN_WORKERS=2
RUN_DB_MIGRATIONS=true
RUN_SEED=false
```

Set secret env vars from Secrets Manager:

```env
JWT_SECRET_KEY -> arn:aws:secretsmanager:...
DEFAULT_ADMIN_PASSWORD -> arn:aws:secretsmanager:...
```

## Stage A8: Networking (critical for RDS private access)

1. Create App Runner VPC Connector in same VPC as RDS.
2. Attach security group `apprunner-sg` to connector.
3. In `rds-sg`, allow inbound `5432` from `apprunner-sg` only.
4. Attach connector to App Runner service.

## Stage A9: Deploy and verify

1. Deploy service.
2. Watch CloudWatch logs.
3. Verify:

```bash
curl -s https://YOUR_APP_RUNNER_URL/api/v1/health
curl -s https://YOUR_APP_RUNNER_URL/api/v1/health/ready
```

## Stage A10: Domain + TLS

1. App Runner -> Custom domains.
2. Add `api.example.com`.
3. Create DNS records in Route 53 or your DNS provider.
4. Wait until TLS certificate is active.
5. Update `ALLOWED_HOSTS` + frontend API URL.

## Stage A11: AWS production operations

1. Keep migration strategy controlled:
   - Recommended: run migration in pipeline/job before scaling out.
2. Keep `RUN_SEED=false` except initial provisioning.
3. Enable CloudWatch alarms for:
   - 5xx rate
   - latency
   - instance count saturation
4. Rotate secrets periodically in Secrets Manager.
5. Tag all resources for cost tracking.

## Stage A12: Deploy frontend on AWS

You can choose one of two AWS frontend hosting paths.

### Option 1: AWS Amplify Hosting (recommended)

1. Open AWS Amplify -> `Host web app`.
2. Connect your Git repository.
3. Set app root to `react`.
4. Add build spec (`amplify.yml`) or configure:
   - Install: `npm ci`
   - Build: `npm run build`
   - Artifacts: `dist`
5. Add environment variable:

```env
VITE_API_BASE_URL=https://api.example.com/api/v1
```

6. Add SPA rewrite/redirect rule:
   - Source address: `/<*>`
   - Target address: `/index.html`
   - Type: `200 (Rewrite)`
7. Deploy and test all routes including `/admin/orders` and `/orders/:orderId`.

### Option 2: S3 + CloudFront

1. Build frontend locally from `ecom/react`:

```bash
npm ci
VITE_API_BASE_URL=https://api.example.com/api/v1 npm run build
```

2. Create S3 bucket for static hosting.
3. Upload `dist/` contents.
4. Create CloudFront distribution pointing to S3.
5. Configure custom error responses for SPA:
   - `403 -> /index.html (200)`
   - `404 -> /index.html (200)`
6. Add custom domain + ACM certificate.
7. In backend, set:
   - `CORS_ORIGINS=https://your-frontend-domain.com`
   - `ALLOWED_HOSTS` includes backend domain
8. Invalidate CloudFront cache after each release:

```bash
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

---

## Stage 4: Post-deploy verification checklist (both platforms)

1. Health endpoints return 200.
2. Register/login flow works.
3. Product list endpoint responds.
4. Cart -> checkout flow works.
5. Payment gateway options endpoint works: `GET /api/v1/orders/payment-gateways/free`.
6. Payment quote works: `POST /api/v1/orders/{order_id}/payment/quote`.
7. Pay endpoint works and applies tax only at payment time: `POST /api/v1/orders/{order_id}/pay`.
8. DB writes persist after restart.
9. Frontend can call backend from production domain.
10. CORS errors are not present.
11. TLS certificate valid.
12. React SPA route refresh works (`/catalog`, `/orders/1`, `/admin/users`).
13. Admin-only pages are blocked for non-admin users.
14. Payment quote and pay responses are reflected in UI.

## Stage 5: Common failure cases and fixes

### Failure: `JWT_SECRET_KEY must be changed in production`

Cause: production env but still default secret.

Fix: set real values (without angle brackets):

```bash
export JWT_SECRET_KEY='real-secret-value'
export DEFAULT_ADMIN_PASSWORD='real-admin-password'
export SEED_DEMO_USERS=false
```

### Failure: `Address already in use` on port 8000

Cause: another app already running on that port.

Fix:

```bash
ss -ltnp | rg ':8000'
pkill -f "uvicorn app.main:app"
```

### Failure: Docs blocked by CSP

Cause: strict CSP applied to docs page.

Fix: already handled in middleware by docs-specific CSP. If custom CSP is changed later, allow Swagger/ReDoc assets.

### Failure: Payment succeeds but tax stays zero

Cause: `apply_tax` is false (default) in pay payload.

Fix: send tax options when calling pay endpoint, for example:

```json
{
  "provider": "manual_free",
  "apply_tax": true,
  "tax_mode": "percent",
  "tax_value": "18.00"
}
```

### Failure: `CORS` blocked in browser

Cause: frontend domain missing in `CORS_ORIGINS`.

Fix: add exact frontend origin (including `https://`).

### Failure: DB connection refused

Cause: wrong `DATABASE_URL` or network path blocked.

Fix:

1. Validate credentials and host.
2. Validate SG/network rules (AWS).
3. Confirm managed DB service is healthy.

---

## Stage 6: CI/CD recommendation (short)

Pipeline order:

1. Run tests (`pytest`).
2. Build Docker image.
3. Push image (ECR or Git-backed Render deploy).
4. Run DB migration.
5. Deploy application.
6. Run smoke tests against `/api/v1/health/ready`.

---

## Official references

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
