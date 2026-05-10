# OYNA Backend

FastAPI backend for the OYNA computer-club platform: authentication, clubs, branches, zones, seats, reservations, sessions, payments.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2 + Alembic
- PostgreSQL 16
- Pydantic Settings
- Pytest + Ruff

## Setup

### 1. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
.venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Minimum required values:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/oyna
JWT_SECRET_KEY=change-me-to-something-random
```

To seed a local admin account on first startup:

```env
DEV_SEED_ADMIN_EMAIL=admin@oyna.kz
DEV_SEED_ADMIN_PASSWORD=yourpassword
DEV_SEED_ADMIN_ROLE=platform_admin
```

### 3. Start PostgreSQL

```bash
docker compose up -d db
```

Or point `DATABASE_URL` at any running PostgreSQL 16 instance.

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload
```

API: `http://localhost:8000`  
Swagger: `http://localhost:8000/docs`

## Docker (full stack)

```bash
docker compose up --build
```

Starts backend + PostgreSQL. Backend on port `8000`.

## Tests

```bash
DATABASE_URL=sqlite:///./ci-test.db JWT_SECRET_KEY=test pytest app/tests
```

## Lint

```bash
ruff check .
ruff format --check .
```

## Health

```
GET /health
GET /api/v1/health
```
