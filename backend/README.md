############# Branches Information #############

# Main Branch :-

## Contains the Open AI based OCR data extractor in Image_text_extractor


# feature/v1-dev :-

## Contains the Tesseract based OCR Data extractor in Image_text_extractor

# feature/version-2 :-

## Contains the new code format which uses only locator not ocr and has a SmartAI concept used during methods generation.

---

## Database Setup

The backend now uses SQLAlchemy with Alembic migrations and persists everything in the centralized database referenced by `DATABASE_URL`. There is no local SQLite fallback—every environment must point to the shared storage so all instances read/write the same data.

1. **Configure the connection string**
   - Copy `.env.example` to `.env` if needed.
   - Set `DATABASE_URL=postgresql+psycopg://user:password@central-host:5432/testify` (or whatever your central Postgres endpoint is) before running any backend processes.

2. **Run migrations**
   ```bash
   alembic -c backend/database/alembic.ini upgrade head
   ```
   This bootstraps the schema (see `backend/database/migrations/`).

3. **Optional: skip auto-create**
   - The app calls `Base.metadata.create_all()` on import for convenience.
   - Set `SQLALCHEMY_SKIP_AUTO_INIT=1` to require migrations instead.

Existing project endpoints (`/projects/save-details`, `/projects`, `/projects/activate`) now persist to the `projects` table and automatically prepare project directories under `backend/<project_name>/...`.

Project file edits performed through the `/projects/{id}/files/*` APIs are duplicated into the `project_files` table so their latest contents are always stored in the shared database (in addition to the on-disk copy the SmartAI runtime still requires).


