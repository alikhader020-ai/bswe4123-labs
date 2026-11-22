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
