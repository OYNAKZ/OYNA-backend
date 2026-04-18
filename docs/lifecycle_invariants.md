# Reservation, Session, and Seat Lifecycle Invariants

## Normalized transitions

### Reservation

- `created` or `confirmed` can be created via reservation creation.
- `confirmed` can transition to `checked_in`.
- `confirmed` or `checked_in` can transition to `session_started`.
- `confirmed` or `checked_in` can transition to `cancelled` if:
  - no active session exists
  - the cancellation window is still open
- `session_started` transitions to `completed` when the linked session is finished.

### Session

- New sessions must start as `active`.
- A session can only be created from a reservation in `confirmed` or `checked_in`.
- `active` transitions to `finished` through session finish.

### Seat operational status

- Reservation/session lifecycle owns:
  - `reserved`
  - `occupied`
- Manual operations own:
  - `available`
  - `maintenance`
  - `offline`

Automatic seat sync rules:

- active session present -> `occupied`
- no active session, active reservation present -> `reserved`
- no active session, no active reservation -> `available`
- existing manual `maintenance` or `offline` status is preserved unless a session is active

## Explicitly illegal transitions

### Reservation

- check-in from `created`
- check-in from `cancelled`
- check-in from `expired`
- check-in from `no_show`
- check-in from `completed`
- check-in after `expires_at`
- starting a session twice
- cancelling after `session_started`
- cancelling after `completed`
- cancelling after `expired`
- cancelling after `no_show`

### Session

- creating a new session with non-`active` initial status
- finishing any non-`active` session

### Seat

- manual change to `reserved`
- manual change to `occupied`
- any manual seat status change while an active session exists
- changing to `available`, `maintenance`, or `offline` while active reservations exist

## Why these guards matter

- Reservation and session state now converge when a session ends.
- Seat status is re-synchronized after cancellation and session finish, so future reservations keep the seat in `reserved` instead of incorrectly dropping to `available`.
- Manual seat operations can no longer override lifecycle-managed booking/session states.
