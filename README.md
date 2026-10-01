# TamboEnergy SolarAI

TamboEnergy SolarAI is an AI-assisted solar monitoring, diagnostics, alerting, maintenance and analytics platform. It combines FastAPI, React, rule-based safety checks and a prototype machine-learning fault classifier.

> SolarAI is currently decision-support software. It is not a certified protective controller and must not replace inverter, battery, electrical or site safety protections.

## Current MVP capabilities

- JWT authentication with admin, technician and customer roles
- Customer and solar-system management
- Live telemetry monitoring
- Device API-key authentication and telemetry ingestion
- Device fleet management with activate/deactivate and admin key rotation
- Device-to-telemetry provenance for hardware-originated readings
- Rule-based fault detection with ML-assisted classification
- Data-quality and rule/ML disagreement handling
- Enforced alert lifecycle: open → acknowledged → resolved
- Diagnostics and maintenance records
- Analytics dashboard
- Interactive device/fault simulator
- Alembic database migrations

## Project structure

```text
backend/     FastAPI API, SQLAlchemy models, services and migrations
frontend/    React + Vite user interface
ml/          Prototype fault model and training assets
simulator/   Device telemetry and fault simulator
```

## 1. Backend setup

From PowerShell:

```powershell
cd backend
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and replace `SECRET_KEY` with a long random secret. For local development, the default SQLite `DATABASE_URL` can be kept.

Run migrations:

```powershell
alembic upgrade head
```

Create the first admin account if needed:

```powershell
python create_admin.py
```

Start the API:

```powershell
python -m uvicorn app.main:app --reload
```

API: `http://127.0.0.1:8000`  
Swagger: `http://127.0.0.1:8000/docs`

## 2. Frontend setup

Open another PowerShell window:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Frontend: `http://localhost:5173`

`VITE_API_BASE_URL` controls which backend the frontend uses. This allows the same frontend code to work locally or in production without editing source files.

## 3. Device simulator

Register or rotate a device API key in SolarAI. Never commit the raw key.

```powershell
cd simulator
Copy-Item .env.example .env
```

Set `DEVICE_API_KEY` in `simulator/.env`, then run the simulator with an environment that has `requests` and `python-dotenv` installed:

```powershell
..\backend\venv\Scripts\python.exe .\simulator.py
```

## Environment variables

### Backend

- `APP_ENV` — `development` or production environment label
- `SECRET_KEY` — JWT signing secret; required
- `ALGORITHM` — JWT algorithm, default `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` — JWT lifetime, default `60`
- `DATABASE_URL` — SQLAlchemy database URL
- `CORS_ORIGINS` — comma-separated allowed frontend origins

### Frontend

- `VITE_API_BASE_URL` — backend API base URL

### Simulator

- `DEVICE_API_KEY` — per-device credential
- `SOLARAI_API_URL` — SolarAI backend URL

## Automated backend tests

Pass 2 adds regression tests for the SolarAI decision engine, device API-key hashing, device telemetry provenance and alert lifecycle transitions.

From `backend/` with the virtual environment active:

```powershell
pytest -q
```

The tests intentionally verify the safety behavior already established during development: safety-critical deterministic rules retain priority when the ML model disagrees, while high-confidence ML results may influence non-safety disagreements and still require review.

## Device provenance

Hardware-originated telemetry is stored with an optional `device_id`. Manual/admin telemetry keeps `device_id` empty. Deleting a registered device preserves historical telemetry and clears the device reference through the database foreign-key policy.

## Production database

The application reads `DATABASE_URL`, so production can use PostgreSQL without changing source code. Example:

```text
postgresql+psycopg2://user:password@host:5432/solarai
```

Run `alembic upgrade head` against the production database before starting the API.

## Security notes

- Never commit `.env` files or raw device API keys.
- Use HTTPS in production.
- Use a strong unique `SECRET_KEY`.
- Device API keys are stored as hashes by the backend.
- The included ML model is a prototype trained on synthetic data and should be improved with validated field telemetry before safety-sensitive operational use.

## Development status

Pass 1 established environment-based configuration and deployment foundations. Pass 2 adds device fleet management, hardware telemetry provenance, a stricter alert lifecycle, role-aware frontend actions and automated backend regression tests. Production security hardening, deployment packaging and final end-to-end release verification remain before the v1.0 MVP release.
