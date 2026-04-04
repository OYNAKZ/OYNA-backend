# API Guide

Base URL: `http://localhost:8000`

API prefix: `/api/v1`

Interactive docs:
- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

## Authentication

Protected endpoints require:

```http
Authorization: Bearer <access_token>
```

Roles used by the API:
- `user`
- `club_admin`
- `owner`
- `platform_admin`

## Quick Start Flow

1. Register a user with `POST /api/v1/auth/register`
2. Log in with `POST /api/v1/auth/login`
3. Use the returned `access_token` as a Bearer token
4. Create clubs, branches, zones, and seats with an admin-capable account
5. Create reservations and sessions
6. Use `/api/v1/operations/*` for operational workflows

## Health

### `GET /health`
Public root health check.

Example:

```bash
curl http://localhost:8000/health
```

Response:

```json
{"status":"ok"}
```

### `GET /api/v1/health`
Health check through the API router. It also verifies DB access.

```bash
curl http://localhost:8000/api/v1/health
```

## Auth

### `POST /api/v1/auth/register`
Creates a regular `user` account.

Request body:

```json
{
  "email": "user@example.com",
  "password": "very-strong-password",
  "full_name": "Test User",
  "phone": "+77001234567"
}
```

Example:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "very-strong-password",
    "full_name": "Test User",
    "phone": "+77001234567"
  }'
```

Response:

```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "Test User",
    "is_email_verified": false,
    "is_active": true,
    "created_at": "2026-03-31T10:00:00Z"
  },
  "verification_required": false,
  "email": "user@example.com",
  "full_name": "Test User"
}
```

Notes:
- Password length is controlled by environment settings.
- Duplicate email or phone returns `409`.

### `POST /api/v1/auth/login`
Accepts either JSON or OAuth-style form data.

JSON example:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "very-strong-password"
  }'
```

Form example:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=very-strong-password"
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

## Users

All `/api/v1/users*` endpoints require authentication.

### `GET /api/v1/users`
Returns all users.

```bash
curl http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /api/v1/users/me`
Returns the authenticated user.

```bash
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /api/v1/users/{user_id}`
Returns a single user by id.

```bash
curl http://localhost:8000/api/v1/users/1 \
  -H "Authorization: Bearer $TOKEN"
```

Example user response:

```json
{
  "id": 1,
  "full_name": "Test User",
  "club_id": null,
  "email": "user@example.com",
  "phone": "+77001234567",
  "role": "user",
  "is_active": true
}
```

## Clubs

All `/api/v1/clubs*` endpoints require authentication.

### `GET /api/v1/clubs`
List clubs.

```bash
curl http://localhost:8000/api/v1/clubs \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /api/v1/clubs`
Allowed roles: `owner`, `platform_admin`

```bash
curl -X POST http://localhost:8000/api/v1/clubs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OYNA Arena",
    "description": "Main club",
    "is_active": true
  }'
```

Response:

```json
{
  "id": 1,
  "name": "OYNA Arena",
  "description": "Main club",
  "is_active": true
}
```

## Branches

All `/api/v1/branches*` endpoints require authentication.

### `GET /api/v1/branches`

```bash
curl http://localhost:8000/api/v1/branches \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /api/v1/branches`
Allowed roles: `club_admin`, `owner`, `platform_admin`

```bash
curl -X POST http://localhost:8000/api/v1/branches \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "club_id": 1,
    "name": "Downtown Branch",
    "address": "123 Main St",
    "city": "Almaty",
    "latitude": 43.2389,
    "longitude": 76.8897,
    "open_time": "09:00:00",
    "close_time": "23:00:00",
    "is_active": true
  }'
```

## Zones

All `/api/v1/zones*` endpoints require authentication.

### `GET /api/v1/zones`

```bash
curl http://localhost:8000/api/v1/zones \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /api/v1/zones`
Allowed roles: `club_admin`, `owner`, `platform_admin`

```bash
curl -X POST http://localhost:8000/api/v1/zones \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "branch_id": 1,
    "name": "VIP Zone",
    "zone_type": "vip",
    "description": "Premium gaming area",
    "is_active": true
  }'
```

## Seats

All `/api/v1/seats*` endpoints require authentication.

### `GET /api/v1/seats`

```bash
curl http://localhost:8000/api/v1/seats \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /api/v1/seats`
Allowed roles: `club_admin`, `owner`, `platform_admin`

```bash
curl -X POST http://localhost:8000/api/v1/seats \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id": 1,
    "code": "A-01",
    "seat_type": "pc",
    "is_active": true,
    "is_maintenance": false,
    "operational_status": "available",
    "x_position": 10,
    "y_position": 20
  }'
```

### `GET /api/v1/seats/{seat_id}/availability?date=YYYY-MM-DD`

```bash
curl "http://localhost:8000/api/v1/seats/1/availability?date=2026-03-31" \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```json
{
  "seat_id": 1,
  "date": "2026-03-31",
  "slots": [
    {
      "start": "2026-03-31T00:00:00Z",
      "end": "2026-03-31T10:00:00Z",
      "status": "free"
    },
    {
      "start": "2026-03-31T10:00:00Z",
      "end": "2026-03-31T12:00:00Z",
      "status": "booked"
    }
  ]
}
```

Notes:
- Seats in `maintenance` or `offline` return a full-day blocked slot.

## Reservations

All `/api/v1/reservations*` endpoints require authentication.

### `GET /api/v1/reservations`
Listing is filtered by role and scope.

```bash
curl http://localhost:8000/api/v1/reservations \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /api/v1/reservations/{reservation_id}`

```bash
curl http://localhost:8000/api/v1/reservations/1 \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /api/v1/reservations`

Regular user creating a reservation for themself:

```bash
curl -X POST http://localhost:8000/api/v1/reservations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "seat_id": 1,
    "start_at": "2026-03-31T18:00:00Z",
    "end_at": "2026-03-31T20:00:00Z"
  }'
```

Staff creating a reservation for another user:

```bash
curl -X POST http://localhost:8000/api/v1/reservations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "seat_id": 1,
    "user_id": 5,
    "start_at": "2026-03-31T18:00:00Z",
    "end_at": "2026-03-31T20:00:00Z",
    "status": "confirmed"
  }'
```

Response:

```json
{
  "id": 1,
  "seat_id": 1,
  "user_id": 5,
  "start_at": "2026-03-31T18:00:00Z",
  "end_at": "2026-03-31T20:00:00Z",
  "status": "confirmed",
  "expires_at": null,
  "cancelled_at": null
}
```

Notes:
- `end_at` must be later than `start_at`
- Overlapping reservations return `409`
- Seats in `maintenance` or `offline` cannot be reserved
- If the seat was `available`, it becomes `reserved`

### `PATCH /api/v1/reservations/{reservation_id}/cancel`

```bash
curl -X PATCH http://localhost:8000/api/v1/reservations/1/cancel \
  -H "Authorization: Bearer $TOKEN"
```

Notes:
- Cancellation is blocked within 15 minutes of `start_at`
- Cancellation is blocked if an active session exists for that reservation
- A reserved seat is returned to `available`

## Sessions

All `/api/v1/sessions*` endpoints require authentication.

### `GET /api/v1/sessions`

```bash
curl http://localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /api/v1/sessions`
Allowed roles: `club_admin`, `owner`, `platform_admin`

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reservation_id": 1,
    "started_at": "2026-03-31T18:05:00Z",
    "planned_end_at": "2026-03-31T20:00:00Z",
    "status": "active"
  }'
```

Notes:
- Reservation must exist and be `confirmed` or `checked_in`
- Session seat and user must match the reservation
- Seat cannot already have an active session
- Seat cannot be `maintenance` or `offline`
- Starting a session changes the reservation to `session_started` and the seat to `occupied`

## Operational Endpoints

All `/api/v1/operations*` endpoints require:
- authenticated user
- role `club_admin`, `owner`, or `platform_admin`
- active scope assignment for owner or club admin

### `GET /api/v1/operations/reservations`
Query params:
- `branch_id`
- `zone_id`
- `seat_id`
- `status`
- `from`
- `to`
- `page`
- `page_size`

Example:

```bash
curl "http://localhost:8000/api/v1/operations/reservations?page=1&page_size=20&status=confirmed" \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /api/v1/operations/sessions`
Query params:
- `active_only`
- `branch_id`
- `page`
- `page_size`

```bash
curl "http://localhost:8000/api/v1/operations/sessions?active_only=true&page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

### `PATCH /api/v1/operations/reservations/{reservation_id}/check-in`

```bash
curl -X PATCH http://localhost:8000/api/v1/operations/reservations/1/check-in \
  -H "Authorization: Bearer $TOKEN"
```

Rules:
- reservation must be in scope
- reservation cannot already be checked in, cancelled, expired, or converted to session
- current time must be within the check-in window: `start_at - 30 minutes` to `end_at`

### `POST /api/v1/operations/reservations/{reservation_id}/start-session`

```bash
curl -X POST http://localhost:8000/api/v1/operations/reservations/1/start-session \
  -H "Authorization: Bearer $TOKEN"
```

Rules:
- reservation must be `confirmed` or `checked_in`
- seat cannot be `maintenance` or `offline`
- there must be no existing session for the reservation
- the seat must not already have an active session

### `PATCH /api/v1/operations/sessions/{session_id}/finish`

```bash
curl -X PATCH http://localhost:8000/api/v1/operations/sessions/1/finish \
  -H "Authorization: Bearer $TOKEN"
```

Rules:
- session must be active
- if the seat is `occupied`, it becomes `available`

### `PATCH /api/v1/operations/seats/{seat_id}/status`

Request body:

```json
{
  "operational_status": "maintenance",
  "reason": "GPU replacement"
}
```

Example:

```bash
curl -X PATCH http://localhost:8000/api/v1/operations/seats/1/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "operational_status": "maintenance",
    "reason": "GPU replacement"
  }'
```

Rules:
- `operational_status` should be one of `available`, `reserved`, `occupied`, `maintenance`, `offline`
- cannot switch to `available` if an active session exists
- cannot switch to `maintenance` if an active session exists
- every change is written to seat status history

### `GET /api/v1/operations/seats/{seat_id}/status-history`

```bash
curl http://localhost:8000/api/v1/operations/seats/1/status-history \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /api/v1/operations/summary`
Optional query param: `branch_id`

```bash
curl "http://localhost:8000/api/v1/operations/summary?branch_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

Response fields:
- active sessions
- active reservations
- occupied, available, maintenance, and offline seat counts
- per-zone load summary

## Owner Endpoints

All `/api/v1/owner*` endpoints require:
- authenticated user
- role `owner` or `platform_admin`

### `GET /api/v1/owner/clubs`

```bash
curl http://localhost:8000/api/v1/owner/clubs \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /api/v1/owner/analytics`
Query params:
- `club_id`
- `period` with values such as `today`, `7d`, `30d`
- `from`
- `to`

Examples:

```bash
curl "http://localhost:8000/api/v1/owner/analytics?period=7d" \
  -H "Authorization: Bearer $TOKEN"
```

```bash
curl "http://localhost:8000/api/v1/owner/analytics?club_id=1&period=today" \
  -H "Authorization: Bearer $TOKEN"
```

```bash
curl "http://localhost:8000/api/v1/owner/analytics?club_id=1&period=custom&from=2026-03-01T00:00:00Z&to=2026-03-31T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

Notes:
- for a custom range, both `from` and `to` are required
- owner scope is enforced per club

### `GET /api/v1/owner/clubs/{club_id}/staff`

```bash
curl http://localhost:8000/api/v1/owner/clubs/1/staff \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /api/v1/owner/staff-assignments`

```bash
curl -X POST http://localhost:8000/api/v1/owner/staff-assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 7,
    "club_id": 1,
    "branch_id": 1,
    "role_in_scope": "club_admin"
  }'
```

Rules:
- target user must exist and be active
- target user role must match `role_in_scope`
- duplicate active assignment returns `409`

### `PATCH /api/v1/owner/staff-assignments/{assignment_id}/deactivate`

```bash
curl -X PATCH http://localhost:8000/api/v1/owner/staff-assignments/3/deactivate \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /api/v1/owner/staff/{user_id}/scope`

```bash
curl http://localhost:8000/api/v1/owner/staff/7/scope \
  -H "Authorization: Bearer $TOKEN"
```

## Common Status Codes

- `200` success
- `201` resource created
- `400` invalid request semantics
- `401` invalid or missing credentials
- `403` insufficient role or scope
- `404` resource not found
- `409` conflict, duplicate, overlap, or invalid lifecycle transition
- `422` validation error

## Common Enum Values

Reservation status:
- `pending`
- `confirmed`
- `checked_in`
- `session_started`
- `cancelled`
- `expired`
- `no_show`

Session status:
- `active`
- `completed`
- `finished`
- `cancelled`
- `expired`

Seat operational status:
- `available`
- `reserved`
- `occupied`
- `maintenance`
- `offline`

Scope role:
- `owner`
- `club_admin`

## End-to-End Example

Create a reservation, check it in, start a session, and finish it:

```bash
# 1. Create reservation
curl -X POST http://localhost:8000/api/v1/reservations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "seat_id": 1,
    "start_at": "2026-03-31T18:00:00Z",
    "end_at": "2026-03-31T20:00:00Z"
  }'

# 2. Check in
curl -X PATCH http://localhost:8000/api/v1/operations/reservations/1/check-in \
  -H "Authorization: Bearer $STAFF_TOKEN"

# 3. Start session
curl -X POST http://localhost:8000/api/v1/operations/reservations/1/start-session \
  -H "Authorization: Bearer $STAFF_TOKEN"

# 4. Finish session
curl -X PATCH http://localhost:8000/api/v1/operations/sessions/1/finish \
  -H "Authorization: Bearer $STAFF_TOKEN"
```
