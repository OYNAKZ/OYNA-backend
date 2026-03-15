# OYNA — Club Platform API

REST API for managing gaming clubs: branches, zones, seats, reservations, sessions, and user auth.

## Tech Stack

- **FastAPI** — web framework
- **SQLAlchemy 2** — ORM
- **Alembic** — migrations
- **PostgreSQL 16** — database
- **python-jose** — JWT tokens
- **passlib[bcrypt]** — password hashing

## Prerequisites

- Python 3.10+
- Docker & Docker Compose

## Setup

### 1. Start the database

```bash
docker-compose up -d
```

This starts PostgreSQL on `localhost:5433`.

### 2. Create `.env`

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/club_platform
JWT_SECRET_KEY=your-secret-key-here
```

### 3. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Auth Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login, returns JWT token |

## Running Tests

```bash
pytest app/tests
```
