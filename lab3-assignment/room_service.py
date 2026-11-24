import os
import time
from typing import Dict, List
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Room Booking Service (Lab 3)")

# Delay in seconds read from environment variable (e.g., ROOM_DELAY=1.5)
BOOKING_DELAY = float(os.getenv("ROOM_DELAY", "0"))

rooms_db: Dict[str, dict] = {}
bookings_db: Dict[str, dict] = {}


class RoomCreate(BaseModel):
    id: str = Field(..., min_length=1)
    building: str = Field(..., min_length=1)
    capacity: int = Field(..., gt=0)


class BookingCreate(BaseModel):
    room_id: str = Field(..., min_length=1)
    day: str = Field(..., min_length=1)
    start_hour: int = Field(..., ge=0, le=23)
    end_hour: int = Field(..., ge=1, le=24)
    purpose: str = Field(..., min_length=1)


def _apply_delay() -> None:
    if BOOKING_DELAY > 0:
        time.sleep(BOOKING_DELAY)


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


@app.get("/health")
def health() -> dict:
    _apply_delay()
    return {"status": "ok", "delay": BOOKING_DELAY}


@app.post("/rooms", status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate) -> dict:
    _apply_delay()
    if room.id in rooms_db:
        raise HTTPException(status_code=409, detail="Room already exists")
    data = room.model_dump()
    rooms_db[room.id] = data
    return data


@app.get("/rooms")
def list_rooms() -> List[dict]:
    _apply_delay()
    return list(rooms_db.values())


@app.put("/bookings/{booking_id}")
def upsert_booking(booking_id: str, booking: BookingCreate) -> dict:
    _apply_delay()
    if booking.end_hour <= booking.start_hour:
        raise HTTPException(status_code=422, detail="end_hour must be greater than start_hour")

    if booking.room_id not in rooms_db:
        raise HTTPException(status_code=404, detail="Room not found")

    payload = {**booking.model_dump(), "id": booking_id}

    # Idempotent retry check
    if booking_id in bookings_db:
        existing = bookings_db[booking_id]
        if existing == payload:
            return existing
        raise HTTPException(status_code=409, detail="Booking ID already used with different details")

    for existing in bookings_db.values():
        if existing["room_id"] == booking.room_id and existing["day"] == booking.day:
            if _overlaps(booking.start_hour, booking.end_hour, existing["start_hour"], existing["end_hour"]):
                raise HTTPException(status_code=409, detail="Room is already booked for this time")

    bookings_db[booking_id] = payload
    return payload


@app.get("/bookings")
def list_bookings() -> List[dict]:
    _apply_delay()
    return list(bookings_db.values())


@app.get("/bookings/{booking_id}")
def get_booking(booking_id: str) -> dict:
    _apply_delay()
    if booking_id not in bookings_db:
        raise HTTPException(status_code=404, detail="Booking not found")
    return bookings_db[booking_id]


@app.delete("/bookings/{booking_id}")
def delete_booking(booking_id: str) -> dict:
    _apply_delay()
    if booking_id not in bookings_db:
        raise HTTPException(status_code=404, detail="Booking not found")
    deleted = bookings_db.pop(booking_id)
    return {"deleted": deleted}
