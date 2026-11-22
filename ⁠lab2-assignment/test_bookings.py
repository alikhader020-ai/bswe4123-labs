import asyncio
import httpx
from service import app


async def run_tests():
  transport = httpx.ASGITransport(app=app)
  async with httpx.AsyncClient(
      transport=transport, base_url="http://testserver"
  ) as client:
    # 1. Create room B205 -> 201
    r = await client.post(
        "/rooms", json={"id": "B205", "building": "B", "capacity": 40}
    )
    print("Create room B205:", r.status_code)

    # 2. Invalid data (end_hour before start_hour) -> 422
    r = await client.put(
        "/bookings/bk-1",
        json={
            "room_id": "B205",
            "day": "2026-11-23",
            "start_hour": 14,
            "end_hour": 12,
            "purpose": "Invalid hours",
        },
    )
    print("Invalid hours (end < start):", r.status_code)

    # 3. Unknown room -> 404
    r = await client.put(
        "/bookings/bk-2",
        json={
            "room_id": "NOPE",
            "day": "2026-11-23",
            "start_hour": 9,
            "end_hour": 10,
            "purpose": "Unknown room",
        },
    )
    print("Booking unknown room:", r.status_code)

    # 4. Create booking bk-10 (10 to 12) -> 201
    payload = {
        "room_id": "B205",
        "day": "2026-11-23",
        "start_hour": 10,
        "end_hour": 12,
        "purpose": "Study group",
    }
    r1 = await client.put("/bookings/bk-10", json=payload)
    print("First PUT bk-10 (10-12):", r1.status_code, r1.json())

    # 5. Retry exact same PUT request -> 200 (idempotent, no duplicate booking)
    r2 = await client.put("/bookings/bk-10", json=payload)
    print("Retry PUT bk-10 (idempotent):", r2.status_code, r2.json())

    # 6. Adjacent non-overlapping booking (12 to 13) -> 201
    r = await client.put(
        "/bookings/bk-11",
        json={
            "room_id": "B205",
            "day": "2026-11-23",
            "start_hour": 12,
            "end_hour": 13,
            "purpose": "Extra lab",
        },
    )
    print("Adjacent booking (12-13):", r.status_code)

    # 7. Overlapping booking (11 to 13 overlaps 10-12) -> 409
    r = await client.put(
        "/bookings/bk-12",
        json={
            "room_id": "B205",
            "day": "2026-11-23",
            "start_hour": 11,
            "end_hour": 13,
            "purpose": "Conflict test",
        },
    )
    print("Overlapping booking (11-13):", r.status_code)

    # 8. Unknown booking GET & DELETE -> 404
    r_get = await client.get("/bookings/does-not-exist")
    print("Get unknown booking:", r_get.status_code)

    r_del = await client.delete("/bookings/does-not-exist")
    print("Delete unknown booking:", r_del.status_code)

    # Check total bookings count (should be 2: bk-10 and bk-11)
    all_bookings = await client.get("/bookings")
    print("Total bookings in store:", len(all_bookings.json()))


if __name__ == "__main__":
  asyncio.run(run_tests())
