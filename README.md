# OYNA Backend

Backend foundation for the OYNA computer-club booking platform.

## Stack

- FastAPI
- SQLAlchemy 2
- Alembic
- PostgreSQL 16
- Pydantic Settings
- Pytest
- Ruff

## Project Run

### 1. Create `.env`

Copy `.env.example` to `.env`.

Required environment variables:

- `APP_NAME`
- `APP_ENV`
- `DEBUG`
- `API_PREFIX`
- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `LOG_LEVEL`

Example local PostgreSQL URL:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oyna
```

### 2. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run database

```bash
docker compose up -d db
```

### 4. Apply migrations

```bash
alembic upgrade head
```

### 5. Start backend

```bash
uvicorn app.main:app --reload
```

## Health Endpoints

- `GET /health`
- `GET /api/v1/health`

## Docker

Start backend and PostgreSQL together:

```bash
docker compose up --build
```

Backend will be available at `http://localhost:8000`.

## Tests

Run all tests:

```bash
pytest app/tests
```

## Quality Checks

```bash
ruff check .
ruff format --check .
pytest app/tests
```

## Notes

- Settings are loaded from `.env`.
- The app fails on startup if required settings such as `DATABASE_URL` or `JWT_SECRET_KEY` are missing.
- Database schema changes must go through Alembic migrations.
