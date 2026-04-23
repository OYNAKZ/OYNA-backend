# Client API Contract Map

Base URL: `http://localhost:8000`

API prefix: `/api/v1`

Auth:

- `POST /api/v1/auth/register` -> public user registration
- `POST /api/v1/auth/login` -> bearer token login
- Protected endpoints require `Authorization: Bearer <token>`

Core resources:

- `GET /api/v1/users`, `GET /api/v1/users/me`, `GET /api/v1/users/{user_id}`
- `GET/POST /api/v1/clubs`
- `GET/POST /api/v1/branches`
- `GET/POST /api/v1/zones`
- `GET/POST /api/v1/seats`, `GET /api/v1/seats/{seat_id}/availability`
- `GET/POST /api/v1/reservations`, `GET /api/v1/reservations/{reservation_id}`
- `POST /api/v1/reservations/holds`
- `PATCH /api/v1/reservations/{reservation_id}/confirm`
- `PATCH /api/v1/reservations/{reservation_id}/cancel`
- `GET/POST /api/v1/sessions`

Operational/admin resources:

- `GET /api/v1/operations/reservations`
- `GET /api/v1/operations/sessions`
- `PATCH /api/v1/operations/reservations/{reservation_id}/check-in`
- `POST /api/v1/operations/reservations/{reservation_id}/start-session`
- `PATCH /api/v1/operations/sessions/{session_id}/finish`
- `PATCH /api/v1/operations/seats/{seat_id}/status`
- `GET /api/v1/operations/seats/{seat_id}/status-history`
- `GET /api/v1/operations/summary`
- `GET /api/v1/owner/clubs`
- `GET /api/v1/owner/analytics`
- `GET /api/v1/owner/clubs/{club_id}/staff`
- `POST /api/v1/owner/staff-assignments`
- `PATCH /api/v1/owner/staff-assignments/{assignment_id}/deactivate`
- `GET /api/v1/owner/staff/{user_id}/scope`

Payments:

- `GET /api/v1/payments`
- `POST /api/v1/payments`
- `GET /api/v1/payments/{payment_id}`
- `POST /api/v1/payments/{payment_id}/reconcile`
- `POST /api/v1/payments/webhooks/{provider}`

Primary WEB consumers:

- login -> `/auth/login`
- current admin profile -> `/users/me`
- users page -> `/users`
- reservations page -> `/reservations` and `/operations/reservations`
- dashboard summary -> `/operations/summary`, `/operations/sessions`, `/payments`
- payments page -> `/payments`
