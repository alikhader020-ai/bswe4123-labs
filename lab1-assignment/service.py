import time
from fastapi import FastAPI

app = FastAPI()


start_time = time.time()


@app.get("/health")
def health_check():
  uptime_seconds = int(time.time() - start_time)
  return {"status": "ok", "uptime_seconds": uptime_seconds}
