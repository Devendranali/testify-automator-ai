# Auto Test Studio

This repository contains:
- `backend/`: FastAPI API, Alembic migrations, report/visualizer serving, project-scoped storage
- `FRONTEND-NEW/`: React frontend
- `docker-compose.yaml`: local/prod-like multi-container deployment entrypoint

## Deployment-critical facts

- The frontend defaults to `/api` in production and only needs `REACT_APP_API_URL` for explicit overrides.
- The backend requires explicit env configuration from the repo-root `.env`.
- Production startup does not run migrations unless `AUTO_MIGRATE=true`.
- Report viewing uses a short-lived HttpOnly cookie created by `POST /reports/session/{project_id}`.
- Project runtime files live under `backend/organizations/<org_slug>/<project_id>-<project_slug>/...`.

## Required env vars

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY`
- `APP_ENV`
- `ALLOWED_ORIGINS`
- `BACKEND_PUBLIC_BASE_URL`

Either:
- `DATABASE_URL`

Or:
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`

Useful optional vars:
- `AUTO_MIGRATE`
- `ALLOWED_ORIGIN_REGEX`
- `OPENAI_API_KEY`
- `REPORT_SESSION_EXPIRE_MINUTES`
- `REPORT_COOKIE_SECURE`
- `VISUALIZER_OUTPUT_DIR`
- `ALLURE_CLI`
- `APP_HOST`
- `APP_PORT`

## Local development

Backend:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8001
```

Frontend:
```bash
cd FRONTEND-NEW
npm install
npm start
```

Recommended local env:
- `APP_ENV=development`
- `ALLOWED_ORIGINS=http://localhost:3000`
- `REACT_APP_API_URL=http://localhost:8001`
- `BACKEND_PUBLIC_BASE_URL=http://localhost:8001`

## Docker / deployment flow

1. Copy `.env.example` to `.env` and fill in production values.
2. Run migrations explicitly before starting the backend:
```bash
docker compose run --rm backend alembic -c /app/database/alembic.ini upgrade head
```
3. Start the stack:
```bash
docker compose up --build
```

Only enable `AUTO_MIGRATE=true` for local/CI convenience. Keep it `false` in production.

## CORS behavior

- Development-like environments (`development`, `dev`, `local`, `test`) fall back to `http://localhost:3000` only if `ALLOWED_ORIGINS` is unset.
- Production requires explicit `ALLOWED_ORIGINS`.
- `ALLOWED_ORIGINS=*` is rejected in production.
- If `ALLOWED_ORIGINS=*` is used in development, CORS credentials are disabled.

## Runtime paths

Per-project runtime data is stored under:
- `backend/organizations/<org_slug>/<project_id>-<project_slug>/generated_runs/src`
- `backend/organizations/<org_slug>/<project_id>-<project_slug>/data`
- `backend/organizations/<org_slug>/<project_id>-<project_slug>/logs`

## Notes

- Allure reports are served from each project's `generated_runs/src/allure-report`.
- Visualizer assets are served under `/visualizer/*`.
- The frontend is intended to be served from `/`, with backend traffic routed through `/api`.
