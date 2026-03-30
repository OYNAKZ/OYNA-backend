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

The example file is preconfigured for Docker Compose, where PostgreSQL is reachable as `db`.
If you run the app directly on your machine, change `DATABASE_URL` to use `localhost`.

Core settings:

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
- `AUTH_PASSWORD_MIN_LEN`
- `AUTH_PASSWORD_MAX_LEN`
- `AUTH_PASSWORD_HASH_SCHEME`

Example local PostgreSQL URL:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oyna
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows PowerShell, use:

```powershell
.venv\Scripts\Activate.ps1
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
DATABASE_URL=sqlite:///./ci-test.db JWT_SECRET_KEY=test-secret pytest app/tests
```

## Quality Checks

```bash
ruff check .
ruff format --check .
DATABASE_URL=sqlite:///./ci-test.db JWT_SECRET_KEY=test-secret pytest app/tests
```

## Notes

- Settings are loaded from `.env`.
- The app fails on startup if required settings such as `DATABASE_URL` or `JWT_SECRET_KEY` are missing.
- Database schema changes must go through Alembic migrations.
- `GET /health` and `GET /api/v1/health` are both available.
- Protected resources include `/api/v1/users`, `/api/v1/clubs`, `/api/v1/branches`, `/api/v1/zones`, `/api/v1/seats`, `/api/v1/reservations`, `/api/v1/sessions`, `/api/v1/operations`, and `/api/v1/owner`.
