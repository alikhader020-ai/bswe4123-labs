# Lab Assignment 3: The Exam Scheduler Service

## Student Info
- **Name:** Ali Khader
- **Student ID:** 120220101
- **Course:** BSWE4123

---

## 1. Commands to Run Both Services

Install dependencies:
```bash
pip install fastapi uvicorn httpx pydantic
```

Run the **Room Booking Service** on port `8001` (with optional delay):
```bash
ROOM_DELAY=0.0 uvicorn room_service:app --host 127.0.0.1 --port 8001
```

Run the **Exam Scheduler Service** on port `8002`:
```bash
ROOM_SERVICE_URL=[http://127.0.0.1:8001](http://127.0.0.1:8001) REQUEST_TIMEOUT=2.0 MAX_RETRIES=3 uvicorn scheduler_service:app --host 127.0.0.1 --port 8002
```

Check active configuration via `GET /config`:
```bash
curl [http://127.0.0.1:8002/config](http://127.0.0.1:8002/config)
```
Response:
```json
{
  "room_service_url": "[http://127.0.0.1:8001](http://127.0.0.1:8001)",
  "request_timeout": 2.0,
  "max_retries": 3
}
```

---

## 2. Retry Test Log & Safety Explanation (Step 3)

### Setup & Test Execution
1. Seeded rooms in `Room Booking Service` (`B101` with capacity `30`, `B205` with capacity `60`).
2. Stopped `Room Booking Service` (`Ctrl+C` on port `8001`).
3. Sent `POST /exams` to `Exam Scheduler Service` (`port 8002`) for exam `EX-101` (`45` students).
4. While the scheduler was retrying with exponential backoff (`0.5s`, `1.0s`, `2.0s`), restarted `Room Booking Service` on port `8001`.

### Test Log
```text
[19:41:02.110] POST [http://127.0.0.1:8002/exams](http://127.0.0.1:8002/exams) {"id":"EX-101","course_code":"BSWE4123","day":"2026-12-10","start_hour":9,"end_hour":11,"students":45}
[19:41:02.118] Attempt 1 -> GET [http://127.0.0.1:8001/rooms](http://127.0.0.1:8001/rooms) failed: ConnectError (Connection refused). Retrying in 0.5s...
[19:41:02.625] Attempt 2 -> GET [http://127.0.0.1:8001/rooms](http://127.0.0.1:8001/rooms) failed: ConnectError (Connection refused). Retrying in 1.0s...
[19:41:03.200] Room Booking Service restarted on [http://127.0.0.1:8001](http://127.0.0.1:8001)
[19:41:03.631] Attempt 3 -> GET [http://127.0.0.1:8001/rooms](http://127.0.0.1:8001/rooms) succeeded (200 OK)
[19:41:03.640] GET [http://127.0.0.1:8001/bookings](http://127.0.0.1:8001/bookings) succeeded (200 OK)
[19:41:03.648] Selected smallest suitable room: B205 (capacity 60 >= 45)
[19:41:03.655] PUT [http://127.0.0.1:8001/bookings/exam-EX-101](http://127.0.0.1:8001/bookings/exam-EX-101) -> 200 OK
[19:41:03.660] Response to client: 201 Created {"exam_id":"EX-101","booked_room":{"id":"B205","building":"B","capacity":60},...}
```

### Why the Booking Request Is Safe to Retry
- **Idempotent `PUT` with Deterministic ID:** The scheduler always books the room using `PUT /bookings/exam-{exam.id}` (e.g., `exam-EX-101`).
- **No Duplicate Bookings:** If a network timeout happens after the Room Booking Service processes the request and the scheduler retries, the Room Booking Service finds `exam-EX-101` already stored with the exact same details and returns the existing booking instead of creating a duplicate.
- **No Retries on `404` or `409`:** Client/business conflicts such as `404 Not Found` or `409 Conflict` (e.g., no room large enough or slot already taken) are returned immediately without wasting retries.

---

## 3. Delay vs. Timeout Experiment (Step 4)

Note: Each successful `POST /exams` performs up to 3 upstream calls (`GET /rooms`, `GET /bookings`, `PUT /bookings/{id}`), so each upstream call experiences `ROOM_DELAY`.

| Combination | `ROOM_DELAY` (s) | `REQUEST_TIMEOUT` (s) | `MAX_RETRIES` | `POST /exams` Status Code | Response Time (s) | Outcome |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Case 1 (Fast / Normal)** | `0.2` | `1.5` | `3` | `201 Created` | `0.64 s` | All 3 calls succeed on first attempt (`3 × 0.2s` + overhead). |
| **Case 2 (Moderate Delay, Generous Timeout)** | `1.0` | `2.0` | `3` | `201 Created` | `3.05 s` | Slower response, but each call finishes before `2.0s` timeout. |
| **Case 3 (High Delay > Timeout)** | `2.5` | `1.0` | `3` | `503 Service Unavailable` | `7.58 s` | Every attempt times out at `1.0s` (`4 × 1.0s` + `0.5s + 1.0s + 2.0s` backoff). |

### Trade-off Explanation
- **Short Timeout (`REQUEST_TIMEOUT` too low):** Detects dead or overloaded services quickly so clients do not wait long, but causes false timeouts and unnecessary retries when the downstream service is merely slow (increasing load even further).
- **Long Timeout (`REQUEST_TIMEOUT` high):** Tolerates temporary slowness and avoids false failures (as in Case 2), but forces clients to wait much longer before failing when the downstream service is genuinely down or hung.
- **Retries with Exponential Backoff:** Help recover from brief outages or restarts, but multiply total latency when every attempt times out (as in Case 3). Therefore, `REQUEST_TIMEOUT` must be tuned slightly above normal worst-case response latency, with a bounded retry count.
