from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field, model_validator

app = FastAPI(title="Campus Room Booking Service")


class RoomCreate(BaseModel):
  id: str = Field(..., min_length=1)
  building: str = Field(..., min_length=1)
  capacity: int = Field(..., gt=0)


class Room(RoomCreate):
  pass


class BookingCreate(BaseModel):
  room_id: str = Field(..., min_length=1)
  day: str = Field(..., min_length=1)
  start_hour: int = Field(..., ge=8, le=20)
  end_hour: int = Field(..., ge=8, le=20)
  purpose: str = Field(..., min_length=1)

  @model_validator(mode="after")
  def validate_hours(self):
    if self.end_hour <= self.start_hour:
      raise ValueError("end_hour must be greater than start_hour")
    return self


class Booking(BookingCreate):
  id: str


rooms_db: dict[str, Room] = {}
bookings_db: dict[str, Booking] = {}


def is_overlapping(
    a_start: int, a_end: int, b_start: int, b_end: int
) -> bool:
  # Two intervals [start, end) overlap iff start1 < end2 and start2 < end1.
  # Adjacent intervals like [10, 12) and [12, 13) do not overlap.
  return a_start < b_end and b_start < a_end


@app.post("/rooms", response_model=Room, status_code=status.HTTP_201_CREATED)
def create_room(room: RoomCreate):
  if room.id in rooms_db:
    raise HTTPException(status_code=409, detail="Room already exists")
  created = Room(**room.model_dump())
  rooms_db[created.id] = created
  return created


@app.get("/rooms", response_model=list[Room])
def list_rooms():
  return list(rooms_db.values())


@app.put("/bookings/{booking_id}", response_model=Booking)
def upsert_booking(booking_id: str, payload: BookingCreate, response: Response):
  if payload.room_id not in rooms_db:
    raise HTTPException(status_code=404, detail="Room not found")

  # Idempotency check: if booking_id already exists with identical payload, return it safely
  if booking_id in bookings_db:
    existing = bookings_db[booking_id]
    if existing.model_dump(exclude={"id"}) == payload.model_dump():
      response.status_code = status.HTTP_200_OK
      return existing
    raise HTTPException(
        status_code=409,
        detail="Booking ID already exists with different details",
    )

  # Overlap check against other bookings on same room and day
  for other_id, other in bookings_db.items():
    if other_id == booking_id:
      continue
    if other.room_id == payload.room_id and other.day == payload.day:
      if is_overlapping(
          payload.start_hour, payload.end_hour, other.start_hour, other.end_hour
      ):
        raise HTTPException(
            status_code=409,
            detail="Booking overlaps with an existing booking",
        )

  new_booking = Booking(id=booking_id, **payload.model_dump())
  bookings_db[booking_id] = new_booking
  response.status_code = status.HTTP_201_CREATED
  return new_booking


@app.get("/bookings", response_model=list[Booking])
def list_bookings():
  return list(bookings_db.values())


@app.get("/bookings/{booking_id}", response_model=Booking)
def get_booking(booking_id: str):
  if booking_id not in bookings_db:
    raise HTTPException(status_code=404, detail="Booking not found")
  return bookings_db[booking_id]


@app.delete("/bookings/{booking_id}", status_code=status.HTTP_200_OK)
def delete_booking(booking_id: str):
  if booking_id not in bookings_db:
    raise HTTPException(status_code=404, detail="Booking not found")
  deleted = bookings_db.pop(booking_id)
  return {"deleted": deleted.id}
