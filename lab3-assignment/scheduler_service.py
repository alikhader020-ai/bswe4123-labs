import os
import time
from typing import Any, Dict, List, Optional
import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Exam Scheduler Service (Lab 3)")

ROOM_SERVICE_URL = os.getenv("ROOM_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "2.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


class ExamScheduleRequest(BaseModel):
    id: str = Field(..., min_length=1)
    course_code: str = Field(..., min_length=1)
    day: str = Field(..., min_length=1)
    start_hour: int = Field(..., ge=0, le=23)
    end_hour: int = Field(..., ge=1, le=24)
    students: int = Field(..., gt=0)


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def _request_with_retry(method: str, path: str, json_body: Optional[dict] = None) -> httpx.Response:
    url = f"{ROOM_SERVICE_URL}{path}"
    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                response = client.request(method, url, json=json_body)

            # Never retry 404 or 409 (and other 4xx client errors)
            if 400 <= response.status_code < 500:
                return response

            # Retry on 5xx server errors
            if response.status_code >= 500:
                last_error = RuntimeError(f"Server returned {response.status_code}")
                if attempt < MAX_RETRIES:
                    backoff = 0.5 * (2 ** attempt)
                    time.sleep(backoff)
                    continue
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Room Booking Service unavailable after retries ({response.status_code})",
                )

            return response

        except HTTPException:
            raise
        except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                backoff = 0.5 * (2 ** attempt)
                time.sleep(backoff)
                continue
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Cannot reach Room Booking Service after {MAX_RETRIES} retries: {exc}",
            )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Room Booking Service unreachable: {last_error}",
    )


@app.get("/config")
def get_config() -> dict:
    return {
        "room_service_url": ROOM_SERVICE_URL,
        "request_timeout": REQUEST_TIMEOUT,
        "max_retries": MAX_RETRIES,
    }


@app.post("/exams", status_code=status.HTTP_201_CREATED)
def schedule_exam(exam: ExamScheduleRequest) -> dict:
    if exam.end_hour <= exam.start_hour:
        raise HTTPException(status_code=422, detail="end_hour must be greater than start_hour")

    # 1. Fetch rooms
    rooms_resp = _request_with_retry("GET", "/rooms")
    if rooms_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch rooms from Room Booking Service",
        )
    rooms: List[Dict[str, Any]] = rooms_resp.json()

    # 2. Fetch existing bookings
    bookings_resp = _request_with_retry("GET", "/bookings")
    if bookings_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to fetch bookings from Room Booking Service",
        )
    bookings: List[Dict[str, Any]] = bookings_resp.json()

    # 3. Filter rooms that fit student count and have no overlapping booking on that day
    suitable_rooms: List[Dict[str, Any]] = []
    for room in rooms:
        if room.get("capacity", 0) < exam.students:
            continue

        is_free = True
        for b in bookings:
            if b.get("room_id") == room.get("id") and b.get("day") == exam.day:
                if _overlaps(exam.start_hour, exam.end_hour, b.get("start_hour", 0), b.get("end_hour", 0)):
                    is_free = False
                    break

        if is_free:
            suitable_rooms.append(room)

    if not suitable_rooms:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No free room large enough for this exam slot",
        )

    # 4. Pick the smallest room that fits
    suitable_rooms.sort(key=lambda r: r.get("capacity", 0))
    chosen_room = suitable_rooms[0]

    # 5. Book using deterministic/client-chosen booking_id for safe retries (idempotency)
    booking_id = f"exam-{exam.id}"
    booking_payload = {
        "room_id": chosen_room["id"],
        "day": exam.day,
        "start_hour": exam.start_hour,
        "end_hour": exam.end_hour,
        "purpose": f"Exam {exam.course_code} ({exam.id})",
    }

    book_resp = _request_with_retry("PUT", f"/bookings/{booking_id}", json_body=booking_payload)

    if book_resp.status_code == 409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Room became unavailable due to a conflicting booking",
        )
    if book_resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Booking failed with status {book_resp.status_code}",
        )

    return {
        "exam_id": exam.id,
        "course_code": exam.course_code,
        "day": exam.day,
        "start_hour": exam.start_hour,
        "end_hour": exam.end_hour,
        "students": exam.students,
        "booked_room": chosen_room,
        "booking": book_resp.json(),
    }
