# Backend Deployment Notes

## Startup

Local:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8001
```

Container startup:
- `backend/entrypoint.sh` waits for Postgres
- runs Alembic only when `AUTO_MIGRATE=true`
- then starts `uvicorn`

## Required backend env vars

- `JWT_SECRET_KEY`
- `APP_ENV`
- `ALLOWED_ORIGINS`

Either:
- `DATABASE_URL`

Or:
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `BACKEND_PUBLIC_BASE_URL`

Optional:
- `AUTO_MIGRATE`
- `ALLOWED_ORIGIN_REGEX`
- `OPENAI_API_KEY`
- `REPORT_SESSION_EXPIRE_MINUTES`
- `REPORT_COOKIE_SECURE`
- `VISUALIZER_OUTPUT_DIR`
- `ALLURE_CLI`
- `APP_HOST`
- `APP_PORT`

## Migrations

Recommended production flow:
```bash
docker compose run --rm backend alembic -c /app/database/alembic.ini upgrade head
docker compose up --build
```

Behavior:
- `AUTO_MIGRATE=true`: startup applies pending Alembic migrations
- `AUTO_MIGRATE=false`: startup validates schema only and exits if the DB is behind

## CORS

- Dev-like `APP_ENV` values: `development`, `dev`, `local`, `test`
- In those environments, missing `ALLOWED_ORIGINS` falls back to `http://localhost:3000`
- Production requires explicit `ALLOWED_ORIGINS`
- `ALLOWED_ORIGINS=*` is rejected in production

## Project storage layout

The backend stores project-scoped files under:
- `backend/organizations/<org_slug>/<project_id>-<project_slug>/generated_runs/src`
- `backend/organizations/<org_slug>/<project_id>-<project_slug>/data`
- `backend/organizations/<org_slug>/<project_id>-<project_slug>/logs`

This is the authoritative layout used by project context resolution, report serving, and visualizer asset lookup.

## Reports and visualizer

- Reports are served under `/reports/*`
- Report auth uses `POST /reports/session/{project_id}` to create a short-lived HttpOnly cookie
- Visualizer endpoints are mounted under `/visualizer/*`
- Visualizer/report URLs must use `BACKEND_PUBLIC_BASE_URL` for any backend-generated external links or browser callbacks
