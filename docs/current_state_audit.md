# OYNA Backend Current State Audit

## Scope

This note captures the current implementation state of the existing OYNA Backend before any new feature work. It is intended to reduce duplicate work and keep future changes incremental and architecture-aligned.

Audit source areas:

- `app/api/router.py`
- `app/api/routes/*`
- `app/models/*`
- `app/services/*`
- `app/repositories/*`
- `app/schemas/*`
- `migrations/versions/*`
- `app/tests/*`

## Architecture Snapshot

- Stack is FastAPI + SQLAlchemy 2 + Alembic + JWT auth.
- The project follows a mostly layered structure:
  - `app/api`: routers and request dependencies
  - `app/services`: business rules and orchestration
  - `app/repositories`: data access
  - `app/models`: ORM entities
  - `app/schemas`: request and response contracts
  - `app/tests`: integration-style API and service-flow coverage
- Protected APIs are grouped behind `get_current_user` in `app/api/router.py`.
- Business logic is concentrated in services for reservations, sessions, operations, auth, and owner workflows.

## Current API Inventory

All protected routes are mounted under `settings.api_prefix`, currently `/api/v1`.

### Public / authentication

- `POST /api/v1/auth/login`
  - Accepts JSON or form payload.
  - Returns bearer JWT on valid credentials.
- `POST /api/v1/auth/register`
  - Registers a user account.
  - Normalizes email to lowercase.
  - Returns a `RegisterResponse`.
- `GET /api/v1/health`
  - DB-backed health check.
- `GET /health`
  - Root-level health check exposed by app wiring and covered by tests.

### Clubs / structure

- `GET /api/v1/clubs`
  - Lists clubs.
- `POST /api/v1/clubs`
  - Allowed for `owner`, `platform_admin`.
- `GET /api/v1/branches`
  - Lists branches.
- `POST /api/v1/branches`
  - Allowed for `club_admin`, `owner`, `platform_admin`.
- `GET /api/v1/zones`
  - Lists zones.
- `POST /api/v1/zones`
  - Allowed for `club_admin`, `owner`, `platform_admin`.
- `GET /api/v1/seats`
  - Lists seats.
- `GET /api/v1/seats/{seat_id}/availability?date=YYYY-MM-DD`
  - Returns merged free/booked daily slots.
- `POST /api/v1/seats`
  - Allowed for `club_admin`, `owner`, `platform_admin`.

### Reservations

- `GET /api/v1/reservations`
  - Scope depends on role.
- `GET /api/v1/reservations/{reservation_id}`
  - Returns nested seat/zone/branch location data.
- `POST /api/v1/reservations`
  - Creates a reservation.
- `PATCH /api/v1/reservations/{reservation_id}/cancel`
  - Cancels an eligible reservation.

### Sessions

- `GET /api/v1/sessions`
  - Scope depends on role.
- `POST /api/v1/sessions`
  - Manual session creation from an eligible reservation.
  - Allowed for `club_admin`, `owner`, `platform_admin`.

### Operations

Mounted under `/api/v1/operations` and gated at router level for `club_admin`, `owner`, `platform_admin`.

- `GET /api/v1/operations/reservations`
  - Filters: `branch_id`, `zone_id`, `seat_id`, `status`, `from`, `to`, `page`, `page_size`
- `GET /api/v1/operations/sessions`
  - Filters: `active_only`, `branch_id`, `page`, `page_size`
- `PATCH /api/v1/operations/reservations/{reservation_id}/check-in`
- `POST /api/v1/operations/reservations/{reservation_id}/start-session`
- `PATCH /api/v1/operations/sessions/{session_id}/finish`
- `PATCH /api/v1/operations/seats/{seat_id}/status`
- `GET /api/v1/operations/seats/{seat_id}/status-history`
- `GET /api/v1/operations/summary`

### Owner / staff / analytics

Mounted under `/api/v1/owner` and gated for `owner`, `platform_admin`.

- `GET /api/v1/owner/clubs`
- `GET /api/v1/owner/analytics`
  - Supports `club_id`, `period`, `from`, `to`
- `GET /api/v1/owner/clubs/{club_id}/staff`
- `POST /api/v1/owner/staff-assignments`
- `PATCH /api/v1/owner/staff-assignments/{assignment_id}/deactivate`
- `GET /api/v1/owner/staff/{user_id}/scope`

### Users

- `GET /api/v1/users`
- `GET /api/v1/users/me`
- `GET /api/v1/users/{user_id}`

## Domain Model Inventory

### `User`

Fields:

- `id`
- `full_name`
- `club_id` nullable FK to `Club`
- `email` unique, indexed, case-insensitive in DB migrations for PostgreSQL
- `phone` unique, nullable
- `password_hash`
- `role`
- `is_active`
- `is_email_verified`
- `email_verified_at`
- timestamp fields from `TimestampMixin`

Relationships:

- `reservations`
- `sessions`
- `club`
- `staff_assignments`
- `seat_status_changes`

### `Club`

Fields:

- `id`
- `name` unique
- `description`
- `is_active`
- timestamps

Relationships:

- `branches`
- `users`
- `staff_assignments`

### `Branch`

Fields:

- `id`
- `club_id`
- `name`
- `address`
- `city`
- `latitude`
- `longitude`
- `open_time`
- `close_time`
- `is_active`
- timestamps

Relationships:

- `club`
- `zones`
- `staff_assignments`

### `Zone`

Fields:

- `id`
- `branch_id`
- `name`
- `zone_type`
- `description`
- `is_active`
- timestamps

Relationships:

- `branch`
- `seats`

### `Seat`

Fields:

- `id`
- `zone_id`
- `code`
- `seat_type`
- `is_active`
- `is_maintenance`
- `operational_status`
- `x_position`
- `y_position`
- timestamps

Constraints and relationships:

- Unique `(zone_id, code)`
- `zone`
- `reservations`
- `sessions`
- `status_history`
- derived `branch` property via `zone.branch`

### `Reservation`

Fields:

- `id`
- `user_id`
- `seat_id`
- `start_at`
- `end_at`
- `status`
- `expires_at`
- `cancelled_at`
- timestamps

Relationships:

- `user`
- `seat`
- `session` one-to-one from business perspective via `Session.reservation_id` unique constraint

### `Session`

Fields:

- `id`
- `reservation_id`
- `seat_id`
- `user_id`
- `started_at`
- `planned_end_at`
- `ended_at`
- `status`
- timestamps

Constraints and relationships:

- Unique `reservation_id`
- `reservation`
- `seat`
- `user`

### `StaffAssignment`

Fields:

- `id`
- `user_id`
- `club_id`
- `branch_id` nullable
- `role_in_scope`
- `is_active`
- timestamps

Relationships:

- `user`
- `club`
- `branch`

### `SeatStatusHistory`

Fields:

- `id`
- `seat_id`
- `changed_by_user_id`
- `from_status`
- `to_status`
- `reason`
- timestamps

Relationships:

- `seat`
- `changed_by`

## Statuses and Lifecycle Rules

### User roles

Current system roles:

- `user`
- `club_admin`
- `owner`
- `platform_admin`

Scope roles used in staff assignments:

- `owner`
- `club_admin`

### Reservation statuses

Defined enum:

- `created`
- `confirmed`
- `checked_in`
- `session_started`
- `cancelled`
- `expired`
- `no_show`
- `completed`

Operationally used today:

- Common creation default is `confirmed`
- `checked_in` is set by operations check-in
- `session_started` is set when a session is started
- `cancelled` is set by cancellation

Defined but not materially managed by workflows:

- `created`
- `expired`
- `no_show`
- `completed`

Active reservation statuses used for overlap/availability/analytics:

- `created`
- `confirmed`
- `checked_in`
- `session_started`

Terminal reservation statuses defined:

- `cancelled`
- `expired`
- `no_show`
- `completed`

### Session statuses

Defined enum:

- `active`
- `completed`
- `finished`
- `cancelled`
- `expired`

Operationally used today:

- `active` on session creation/start
- `finished` on manual finish

Defined but not materially managed by workflows:

- `completed`
- `cancelled`
- `expired`

### Seat operational statuses

Defined enum:

- `available`
- `reserved`
- `occupied`
- `maintenance`
- `offline`

### Implemented transitions

Reservation transitions currently implemented:

- `confirmed` -> `checked_in`
  - Via `/operations/reservations/{id}/check-in`
  - Allowed only inside check-in window and if not expired/cancelled/started
- `confirmed` -> `session_started`
  - Via direct session start from reservation
- `checked_in` -> `session_started`
  - Via direct session start from reservation
- `*` -> `cancelled`
  - Via reservation cancel if outside 15-minute lockout and no active session

Session transitions currently implemented:

- `active` -> `finished`
  - Via `/operations/sessions/{id}/finish`

Seat status transitions currently implemented:

- `available` -> `reserved`
  - On reservation creation
- `reserved` -> `available`
  - On reservation cancellation
- `reserved` or `available` -> `occupied`
  - On session start
- `occupied` -> `available`
  - On session finish
- Any status -> admin-selected operational status
  - Via `/operations/seats/{id}/status`
  - History row is recorded

### Availability and overlap behavior

Current overlap protection:

- Reservation creation checks `ReservationRepository.has_overlap(...)`
- Overlap logic blocks any intersecting reservation in active reservation statuses
- Availability endpoint merges:
  - active reservation intervals
  - non-cancelled session intervals

Current limits:

- No database exclusion constraint for reservation time ranges
- Overlap prevention is application-side only
- No reservation hold TTL sweeper or automatic transition to `expired`
- No explicit synchronization or idempotency around repeated create/start calls

## Permission Model and Role Scoping

### Authentication

- All non-auth APIs are behind `get_current_user`.
- JWT `sub` is resolved to user id.
- Inactive users are rejected.

### Router-level role gates

- `clubs.POST`: `owner`, `platform_admin`
- `branches.POST`: `club_admin`, `owner`, `platform_admin`
- `zones.POST`: `club_admin`, `owner`, `platform_admin`
- `seats.POST`: `club_admin`, `owner`, `platform_admin`
- `sessions.POST`: `club_admin`, `owner`, `platform_admin`
- Entire `operations` router: `club_admin`, `owner`, `platform_admin`
- Entire `owner` router: `owner`, `platform_admin`

### Service-level scope enforcement

Additional scope checks are implemented in `app/services/policies.py`.

Key behaviors:

- `platform_admin`
  - Global visibility and management
- `owner`
  - Scope comes from active `StaffAssignment` rows with `role_in_scope=owner`
  - `create_club` also auto-creates an owner assignment for the newly created club
- `club_admin`
  - Scope comes from active `StaffAssignment` rows with `role_in_scope=club_admin`
  - Fallback to `user.club_id` exists in `admin_scope(...)` if no assignment rows exist

Scope helpers:

- `owner_club_ids(...)`
- `admin_scope(...)`
- `can_manage_club(...)`
- `can_manage_branch(...)`
- `reservation_scope_clause(...)`
- `ensure_can_view_owner_club(...)`
- `ensure_can_operate_reservation(...)`
- `ensure_can_operate_session(...)`
- `ensure_can_operate_seat(...)`
- `ensure_active_scope_assignment(...)`

### Effective reservation/session visibility

- `user`
  - Own reservations and own sessions only
- `club_admin`
  - Reservations/sessions for assigned club or branch scope
- `owner`
  - Reservations/sessions and analytics for owned clubs only
- `platform_admin`
  - Global

## Migrations Inventory

### `0001_create_users_table`

- Creates `users`

### `939e27db035a_create_club_structure_tables`

- Creates `clubs`
- Creates `branches`
- Creates `zones`
- Creates `seats`

### `d3106be2bdb8_create_reservations_and_sessions_tables`

- Creates `reservations`
- Creates `sessions`

### `20260322_auth_integrity`

- Makes `full_name` nullable
- Makes `phone` nullable
- Expands `password_hash`
- Adds email verification fields
- Hardens email storage for PostgreSQL

### `20260325_add_user_club_id`

- Adds `users.club_id`

### `20260330_club_ops_owner`

- Adds `seats.operational_status`
- Backfills seat operational status
- Creates `staff_assignments`
- Creates `seat_status_history`

## Test Coverage Inventory

### Foundation and config

- Root health endpoint
- API health endpoint
- Missing `DATABASE_URL` config failure
- Missing `JWT_SECRET_KEY` config failure

### Auth

- Registration success
- Duplicate email rejection
- Duplicate phone rejection
- Login success
- Wrong password rejection
- Unknown email rejection
- Email normalization on registration
- Password hashing verification
- Password length validation
- Invalid email validation
- Concurrent duplicate registration race returns `201` + `409`

### Club structure CRUD

- Create/list clubs
- Create/list branches
- Create/list zones
- Create/list seats
- Seat code uniqueness inside zone

### Reservations

- Basic reservation creation
- Official reservation status enum is fixed
- Reservation detail view with nested location payload
- Club admin can view reservation in own scope
- Foreign user cannot view another user reservation
- Reservation cancel success
- Cancel blocked by active session
- Cancel blocked near start time

### Seat availability

- Fully free day
- Partially booked day with reservation and ended session intervals
- Fully booked day

### Club operations and owner workflows

- Club admin operational lifecycle:
  - list reservations
  - check-in
  - start session
  - finish session
  - repeated finish conflict
- Out-of-scope club admin check-in forbidden
- Seat maintenance change blocks new reservations and records history
- Owner club overview
- Owner analytics access
- Staff assignment creation
- Staff scope retrieval
- Owner forbidden from foreign-club analytics

### What tests do not currently cover well

- Unauthorized access matrix across all routers
- Negative scope cases for every owner/admin endpoint
- Reservation overlap race conditions under concurrent create attempts
- Expiry handling for `expires_at`
- No-show and completion flows
- Session creation endpoint edge cases beyond operational flow
- Seat `offline` state behavior
- Pagination bounds and filter combinations
- Idempotency or repeated request behavior
- Branch-level assignment nuances
- Users endpoints visibility/privacy rules

## Current Production Gaps

The following areas are missing or only partially scaffolded relative to a production-ready OYNA platform.

### 1. Payment flow

Missing:

- Payment entity/model
- Payment status model and state machine
- Provider integration abstraction
- Webhook handling
- Payment reconciliation
- Refund flow
- Reservation-to-payment linkage
- Audit trail for financial events

Impact:

- Reservations are effectively free or pre-confirmed.
- No support for pending/authorized/failed/refunded payment states.

### 2. Reservation hold / pending payment / TTL

Current state:

- `ReservationStatus.CREATED` and `expires_at` exist.
- No service currently creates a payment hold or temporary reservation hold workflow.
- No sweeper/task marks expired reservations.
- No hold-confirmation transition after successful payment.

Missing:

- Hold creation endpoint/service behavior
- TTL expiration worker or scheduled cleanup
- Pending payment timeout handling
- Seat release on hold expiration
- Idempotent reservation confirmation

### 3. Self-service check-in via QR/token

Current state:

- Check-in exists only as staff/operations action.
- Window logic exists and can be reused.

Missing:

- User-facing check-in endpoint
- Short-lived reservation check-in token / QR payload
- Anti-replay validation
- Device/session binding rules
- Arrival proof or geofence/branch-scoped validation

### 4. Session extension

Current state:

- No session extension API or service.
- Overlap logic exists for reservations but not for extending active sessions.

Missing:

- Extension eligibility rules
- Conflict check against future reservations/sessions
- Price recalculation / payment extension flow
- Updated `planned_end_at` rules
- Idempotent extension command

### 5. Device / PC agent foundation

Missing:

- Device or workstation identity model
- Agent authentication
- Heartbeat/presence model
- Command queue / command acknowledgment
- Remote launch/lock/logout/session sync semantics
- Device-to-seat binding

### 6. Realtime updates

Missing:

- WebSocket or event streaming layer
- Change publication for seat status, reservation, session events
- Backpressure/reconnect model
- Event schema versioning

### 7. Notifications

Current state:

- `app/services/events.py` is only a no-op hook for user registration.

Missing:

- Notification domain model
- Delivery channels: push, email, SMS, in-app
- Event triggers for reservation reminders, payment results, check-in window, session nearing end
- Retry and dead-letter behavior

### 8. Analytics aggregation

Current state:

- Owner analytics are computed with live queries against operational tables.
- Metrics are basic counts and occupancy ratios.

Missing:

- Pre-aggregated analytics tables/materialized views
- Time-bucketed revenue/session/utilization trends
- Cohort and retention analytics
- Zone/branch/seat historical performance snapshots
- Payment-linked analytics

### 9. Reliability / idempotency hardening

Missing or weak:

- Idempotency keys for create/start/finish/payment-confirm commands
- Database-level range exclusion constraints for seat bookings
- Transactional locking for concurrent seat reservation/session start
- Automatic expiry/no-show/completion jobs
- Outbox/event delivery guarantees
- Structured audit logs for critical lifecycle operations

### 10. Observability and operations hardening

Missing:

- Domain metrics
- Tracing
- Structured business-event logs
- Error taxonomy and correlation ids
- Rate limiting and abuse controls
- Background worker/process definitions

## Obvious Inconsistencies and Risks

These were found during audit and should be handled deliberately later rather than silently refactored.

### Statuses defined but not fully operationalized

- Reservation statuses `created`, `expired`, `no_show`, `completed` are defined but not transitioned by current workflows.
- Session statuses `completed`, `cancelled`, `expired` are defined but not managed by active services.

### Reservation/session completion linkage is incomplete

- Finishing a session sets session status to `finished`.
- The related reservation is not moved to `completed`.

### Seat status can drift from true availability

- Creating a reservation marks the seat as `reserved` immediately, even for far-future reservations.
- If multiple future reservations are allowed on the same seat across different times, one seat-level status cannot accurately represent all future occupancy states.

### Direct session creation is less scoped than operational session start

- `POST /api/v1/sessions` is router-gated by role but does not accept `current_user` and does not perform branch/club scope checks.
- That means any staff role may be able to create a session from any eligible reservation if they know the reservation id.

### Create branch/zone/seat APIs are role-gated but not scope-gated

- `POST /branches`, `POST /zones`, and `POST /seats` check role only.
- They do not verify that the acting owner/admin manages the target club/branch.

### Users endpoints appear overexposed

- `GET /api/v1/users` and `GET /api/v1/users/{id}` are only behind authentication, not role or scope checks.
- Current tests do not validate whether this is intentional.

### Fallback admin scoping is mixed

- `club_admin` scope may come from active `StaffAssignment` or fallback `user.club_id`.
- This creates two parallel scoping sources that future work must treat carefully.

### Overlap protection is not DB-enforced

- Reservation overlap logic is currently service-side only.
- Concurrent requests can still race without row locks or exclusion constraints.

## Recommended Next Implementation Order

This order stays aligned with the existing code and current risks.

1. Harden permission and scope invariants.
   - Close role-only holes on create endpoints.
   - Scope `sessions.POST`.
   - Decide and document intended visibility for `/users`.

2. Harden booking invariants and concurrency.
   - Add DB-backed overlap protection or locking strategy.
   - Revisit seat-level `reserved` semantics versus time-based availability.

3. Introduce reservation hold and payment-ready state machine.
   - Use `created` and `expires_at` intentionally.
   - Add expiration handling and seat release.

4. Add self-service check-in.
   - Reuse current check-in window rules.
   - Add secure token/QR contract.

5. Add session extension flow.
   - Reuse overlap logic and pricing hooks.

6. Add device/PC agent foundation.
   - Start with device identity, auth, and heartbeat.

7. Add notifications and realtime event contracts.
   - Prefer event hooks/outbox patterns over ad hoc callbacks.

8. Evolve analytics beyond live operational queries.
   - Add aggregated data structures after lifecycle and payments stabilize.

9. Add observability and idempotency hardening around critical commands.

## Summary

The backend already has a usable operational core:

- JWT auth
- role-aware access
- club structure CRUD
- reservation creation/detail/cancel
- session creation and operations lifecycle
- owner visibility and staff assignment workflows
- Alembic-backed schema history
- integration tests for major flows

The main gaps are not basic CRUD. They are production-readiness gaps around lifecycle completeness, scope hardening, payment/hold flows, self-service check-in, extension logic, device integration, realtime/notifications, and concurrency-safe reliability.
