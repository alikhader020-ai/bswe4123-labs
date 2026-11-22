# Lab Assignment 2: A Campus Room Booking Service

## Student Info
- **Name:** Ali Khader
- **Student ID:** 120220101
- **Course:** BSWE4123

---

## Step 1: API Design

| Operation | Method | URI | Request Body | Success Code | Error Codes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Create Room | `POST` | `/rooms` | `{"id": "B205", "building": "B", "capacity": 40}` | `201` | `422`, `409` |
| List Rooms | `GET` | `/rooms` | None | `200` | None |
| Create/Idempotent Booking | `PUT` | `/bookings/{booking_id}` | `{"room_id": "B205", "day": "2026-11-23", "start_hour": 10, "end_hour": 12, "purpose": "Study"}` | `201` / `200` | `422`, `404`, `409` |
| List Bookings | `GET` | `/bookings` | None | `200` | None |
| Get Booking | `GET` | `/bookings/{booking_id}` | None | `200` | `404` |
| Delete Booking | `DELETE` | `/bookings/{booking_id}` | None | `200` | `404` |

---

## Step 3: Client Script Output (`test_bookings.py`)

```text
Create room B205: 201
Invalid hours (end < start): 422
Booking unknown room: 404
First PUT bk-10 (10-12): 201 {'room_id': 'B205', 'day': '2026-11-23', 'start_hour': 10, 'end_hour': 12, 'purpose': 'Study group', 'id': 'bk-10'}
Retry PUT bk-10 (idempotent): 200 {'room_id': 'B205', 'day': '2026-11-23', 'start_hour': 10, 'end_hour': 12, 'purpose': 'Study group', 'id': 'bk-10'}
Adjacent booking (12-13): 201
Overlapping booking (11-13): 409
Get unknown booking: 404
Delete unknown booking: 404
Total bookings in store: 2
```

---

## Step 4: Safe Retries (Idempotency)
Using `PUT /bookings/{booking_id}` with a client-chosen `booking_id` makes booking creation safe to retry. If the response is lost and the client sends the exact same request again:
1. The server checks if `booking_id` already exists in `bookings_db`.
2. Because the booking details match the stored booking, no duplicate booking is created and the server safely returns `200 OK` with the existing booking.


