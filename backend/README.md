############# Branches Information #############

# Main Branch :-

## Contains the Open AI based OCR data extractor in Image_text_extractor


# feature/v1-dev :-

## Contains the Tesseract based OCR Data extractor in Image_text_extractor

# feature/version-2 :-

## Contains the new code format which uses only locator not ocr and has a SmartAI concept used during methods generation.

---

## Database Setup

The backend now uses SQLAlchemy with Alembic migrations. By default it falls back to the local SQLite file `backend/test.db`, but production/staging deployments should supply a PostgreSQL URL.

1. **Configure the connection string**
   - Copy `.env.example` to `.env` if needed.
   - Add `DATABASE_URL=postgresql+psycopg://user:password@host:5432/testify`.
   - To keep using SQLite for local runs, omit the variable or set `DATABASE_URL=sqlite:///backend/test.db`.

2. **Run migrations**
   ```bash
   alembic -c backend/alembic.ini upgrade head
   ```
   This bootstraps the schema (see `backend/migrations/`).

3. **Optional: skip auto-create**
   - The app calls `Base.metadata.create_all()` on import for convenience.
   - Set `SQLALCHEMY_SKIP_AUTO_INIT=1` to require migrations instead.

Existing project endpoints (`/projects/save-details`, `/projects`, `/projects/activate`) now persist to the `projects` table and automatically prepare project directories under `backend/<project_name>/...`.

