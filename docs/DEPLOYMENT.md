# SolarAI v1 deployment guide

## Backend

Use Python 3.12 and PostgreSQL for production. The backend container runs Alembic before Uvicorn starts.

Required production settings:

```text
APP_ENV=production
APP_VERSION=1.0.0
SECRET_KEY=<32+ character random secret>
DATABASE_URL=postgresql+psycopg2://...
CORS_ORIGINS=https://your-frontend-domain
ALLOWED_HOSTS=your-api-domain
DEVICE_REQUEST_SIGNING_REQUIRED=true
DEVICE_REQUEST_MAX_SKEW_SECONDS=300
DEVICE_RATE_LIMIT_PER_MINUTE=30
DEVICE_NONCE_RETENTION_HOURS=24
```

The hosting platform should terminate HTTPS and pass traffic to the container over its private network. Do not expose PostgreSQL publicly unless the provider requires it and access is restricted.

Health probes:

- `/health` confirms the API process is alive.
- `/health/ready` confirms the API can reach its database.

## Frontend

Build the Vite app with:

```text
VITE_API_BASE_URL=https://your-api-domain
```

Run `npm ci` followed by `npm run build`; deploy the generated `frontend/dist` directory through a static frontend host.

## Database migration

Before first production traffic, run:

```text
alembic upgrade head
```

Never copy the development SQLite database into production. Create users, systems and devices in the production database through the supported application/admin flows.

## Device rollout

Register each gateway separately. Save its raw API key securely when SolarAI displays it. Configure the gateway with the HTTPS API URL and that key. Rotate a key immediately if it is exposed.

The included simulator can be used as a pre-deployment smoke test because it implements request signing, nonces and event IDs.

## CI

`.github/workflows/ci.yml` runs backend migrations/tests and a frontend production build on pushes and pull requests.
